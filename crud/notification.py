from datetime import datetime

from sqlalchemy import select, update
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

    async def crud_get_user_notifications(
            self,
            db: AsyncSession,
            user_uid: str,
            page: int = 1,
            page_size: int = 20,
            unread_only: bool = False
    ):
        """获取用户的通知列表"""
        stmt = select(Notification).where(Notification.recipient_uid == user_uid)
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)

        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        result = await db.execute(count_stmt)
        total = result.scalar_one_or_none()

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
