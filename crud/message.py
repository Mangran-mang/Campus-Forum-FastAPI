from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from models.model_conversation import Conversation
from models.model_message import Message
from models.model_user import User
from tools.exceptions import UserException


class MessageService:
    """私信业务：会话管理 + 消息收发 + 用户搜索"""

    @staticmethod
    def _normalize_pair(uid_a: str, uid_b: str) -> tuple[str, str]:
        """把两个 uid 排序（小的在前），保证 A-B 与 B-A 查到同一个会话"""
        return (uid_a, uid_b) if uid_a < uid_b else (uid_b, uid_a)

    # ============ 会话 ============

    async def crud_get_or_create_conversation(
            self,
            db: AsyncSession,
            current_uid: str,
            other_uid: str
    ) -> Conversation:
        """
        获取或创建与对方的会话（幂等）。
        不允许和自己创建会话。
        """
        if current_uid == other_uid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能和自己私信")

        # 校验对方用户存在
        other_result = await db.execute(select(User).where(User.uid == other_uid))
        other_user = other_result.scalar_one_or_none()
        if not other_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

        # 规范化排序后查询已有会话
        user_a, user_b = self._normalize_pair(current_uid, other_uid)
        stmt = select(Conversation).where(
            Conversation.user_a_uid == user_a,
            Conversation.user_b_uid == user_b
        )
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()
        if conv:
            await self._attach_other_user(db, conv, current_uid)
            return conv

        conv = Conversation(user_a_uid=user_a, user_b_uid=user_b)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        await self._attach_other_user(db, conv, current_uid)
        return conv

    async def _attach_other_user(
            self,
            db: AsyncSession,
            conv: Conversation,
            current_uid: str
    ) -> None:
        """把对方用户对象挂到 conv._other_user（用于序列化）"""
        other_uid = conv.user_b_uid if conv.user_a_uid == current_uid else conv.user_a_uid
        conv._other_uid = other_uid
        result = await db.execute(select(User).where(User.uid == other_uid))
        conv._other_user = result.scalar_one_or_none()

    async def crud_get_user_conversations(
            self,
            db: AsyncSession,
            current_uid: str,
            page: int = 1,
            page_size: int = 20
    ) -> tuple[int, list[Conversation]]:
        """
        获取当前用户的所有会话（按最后消息时间倒序），
        返回 (总数, 会话列表)，每个会话附带对方用户信息与最后一条消息。
        """
        stmt = select(Conversation).where(
            or_(
                Conversation.user_a_uid == current_uid,
                Conversation.user_b_uid == current_uid
            )
        ).order_by(Conversation.updated_time.desc())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        result = await db.execute(count_stmt)
        total = result.scalar_one_or_none()

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        result = await db.execute(stmt)
        conversations = list(result.scalars().all())

        # 加载对方用户信息与最后一条消息（避免 N+1）
        for conv in conversations:
            await self._attach_other_user(db, conv, current_uid)
        await self._load_last_messages(db, conversations)

        return total, conversations

    async def _load_last_messages(self, db: AsyncSession, conversations: list[Conversation]) -> None:
        """批量加载每个会话的最后一条消息，挂到 conv._last_message"""
        conv_ids = [c.id for c in conversations]
        if not conv_ids:
            return
        # 用子查询取每个会话的最大消息 id
        subq = (
            select(Message.conversation_id, func.max(Message.id).label("max_id"))
            .where(Message.conversation_id.in_(conv_ids))
            .group_by(Message.conversation_id)
            .subquery()
        )
        stmt = (
            select(Message)
            .join(subq, Message.id == subq.c.max_id)
        )
        result = await db.execute(stmt)
        last_map = {m.conversation_id: m for m in result.scalars().all()}
        # 批量加载发送者信息
        sender_uids = {m.sender_uid for m in last_map.values()}
        if sender_uids:
            result = await db.execute(select(User).where(User.uid.in_(sender_uids)))
            senders = {u.uid: u for u in result.scalars().all()}
            for m in last_map.values():
                m._sender = senders.get(m.sender_uid)
        for conv in conversations:
            conv._last_message = last_map.get(conv.id)

    async def crud_get_conversation(
            self,
            db: AsyncSession,
            conv_id: int,
            current_uid: str
    ) -> Conversation:
        """按 id 获取会话，并校验当前用户是参与者之一，返回空或会话对象"""
        stmt = select(Conversation).where(Conversation.id == conv_id)
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
        if current_uid not in (conv.user_a_uid, conv.user_b_uid):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该会话")
        return conv

    # ============ 消息 ============

    async def crud_get_messages(
            self,
            db: AsyncSession,
            conv_id: int,
            current_uid: str,
            page: int = 1,
            page_size: int = 50
    ) -> tuple[int, list[Message]]:
        """获取会话历史消息（时间倒序分页），仅会话参与者可读"""
        conv = await self.crud_get_conversation(db, conv_id, current_uid)

        stmt = select(Message).where(Message.conversation_id == conv.id)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        result = await db.execute(count_stmt)
        total = result.scalar_one_or_none()

        offset = (page - 1) * page_size
        result = await db.execute(
            stmt.order_by(Message.created_time.desc()).offset(offset).limit(page_size)
        )
        messages = list(result.scalars().all())
        messages.reverse()  # 倒序取回后再转正序，方便前端直接渲染

        # 批量加载发送者信息
        sender_uids = {m.sender_uid for m in messages}
        if sender_uids:
            result = await db.execute(select(User).where(User.uid.in_(sender_uids)))
            senders = {u.uid: u for u in result.scalars().all()}
            for m in messages:
                m._sender = senders.get(m.sender_uid)

        return total, messages

    async def crud_add_message(
            self,
            db: AsyncSession,
            conv_id: int,
            current_uid: str,
            content: str
    ) -> Message:
        """发送消息：写入消息 + 更新会话的最后消息时间（同一事务）"""
        conv = await self.crud_get_conversation(db, conv_id, current_uid)

        orm_msg = Message(
            conversation_id=conv.id,
            sender_uid=current_uid,
            content=content
        )
        db.add(orm_msg)
        conv.updated_time = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(orm_msg)

        # 附带发送者信息
        result = await db.execute(select(User).where(User.uid == current_uid))
        orm_msg._sender = result.scalar_one_or_none()
        return orm_msg

    # ============ 用户搜索 ============

    async def crud_search_users(
            self,
            db: AsyncSession,
            keyword: str,
            exclude_uid: str,
            limit: int = 10
    ) -> list[User]:
        """按昵称/用户名/邮箱模糊搜索用户（排除自己）"""
        kw = f"%{keyword}%"
        stmt = (
            select(User)
            .where(
                User.uid != exclude_uid,
                or_(
                    User.nickname.like(kw),
                    User.username.like(kw),
                    User.email.like(kw)
                )
            )
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
