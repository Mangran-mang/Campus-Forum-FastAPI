from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import func

from models.model_notification import Notification


class NotificationService:
    async def crud_add_notification(self, db: AsyncSession, notif_data: dict):
        """
        新增通知
        notif_data: {
            "recipient_uid": str,
            "sender_uid": str | None,
            "notif_type": str,
            "post_id": int | None,
            "content": str
        }
        """
        orm_notif = Notification(**notif_data)
        db.add(orm_notif)
        await db.commit()
        await db.refresh(orm_notif)
        return orm_notif

    async def crud_add_notifications(
            self, db: AsyncSession, notif_list: list[dict]
            ):
        """批量新增通知（一次事务）"""
        orm_list = [Notification(**data) for data in notif_list]
        db.add_all(orm_list)
        await db.commit()
        return orm_list

    async def crud_get_user_notifications(
            self,
            db: AsyncSession,
            user_uid: str,
            page: int = 1,
            page_size: int = 20,
            unread_only: bool = False
    ):
        """获取用户的通知列表"""
        # 查找指定用户的所有通知,如果要求只查找未读通知，则添加过滤条件
        stmt = select(Notification).where(Notification.recipient_uid == user_uid)
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)

        # 计算总数的查询语句
        count_stmt = select(func.count()).select_from(stmt.subquery())
        result = await db.execute(count_stmt)
        total = result.scalar_one_or_none()# 用scalar_one更合理

        # 分页查询
        offset = (page - 1) * page_size
        stmt = stmt.order_by(Notification.created_time.desc()).offset(offset).limit(page_size)
        result = await db.execute(stmt)
        notifications = result.scalars().all()

        return total, notifications

    async def crud_mark_as_read(self, db: AsyncSession, notif_id: int, user_uid: str):
        """标记单条通知为已读"""
        stmt = (
            update(Notification)
            .where(Notification.id == notif_id, Notification.recipient_uid == user_uid)
            .values(is_read=True, read_time=datetime.now())
        )
        await db.execute(stmt)
        await db.commit()
        return True

    async def crud_mark_all_as_read(self, db: AsyncSession, user_uid: str):
        """标记所有通知为已读"""
        stmt = (
            update(Notification)
            .where(Notification.recipient_uid == user_uid, Notification.is_read == False)
            .values(is_read=True, read_time=datetime.now())
        )
        await db.execute(stmt)
        await db.commit()
        return True

    async def crud_get_unread_count(self, db: AsyncSession, user_uid: str):
        """获取未读通知数"""
        stmt = select(func.count()).where(
            Notification.recipient_uid == user_uid,
            Notification.is_read == False
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() or 0

    async def crud_clear_read(self, db: AsyncSession, user_uid: str) -> int:
        """
        清空自己的已读通知，返回实际删除的条数

        ## 为什么只清"已读"，不做"清空全部"
        未读是用户还没看到的信息，替他删掉等于替他丢弃 —— 而"清空全部"最容易
        造成"我明明收到过通知"的困惑。把边界画在 is_read 上：用户删掉的每一条
        都是他自己看过、决定不要的。要清未读，让他先标记已读（已有那个功能）。

        ## 为什么返回条数而不是 True
        前端要提示"已清理 N 条"。二次确认之后的反馈给出具体数字，用户才能确认
        这次操作真的做了什么（真删了 3 条 vs 一条都没有）。
        """
        stmt = delete(Notification).where(
            Notification.recipient_uid == user_uid,
            Notification.is_read == True,
        )
        result = await db.execute(stmt)
        await db.commit()
        # rowcount 是本次 DELETE 实际影响的行数
        return result.rowcount or 0
