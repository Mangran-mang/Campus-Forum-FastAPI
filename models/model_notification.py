from datetime import datetime

from sqlalchemy import (
    Integer, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from models.model_base import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        # UniqueConstraint("recipient_uid", "post_id", "created_time", name="uq_notification_recipient_post"),
        # ## 索引列的选择依据（2026-09-26）
        # 对齐 crud/notification.py::crud_get_user_notifications 的查询形状：
        #     WHERE recipient_uid = ?  [AND is_read = false]  ORDER BY created_time DESC
        # 所以三个列都留在索引里 —— recipient_uid 过滤、is_read 过滤、created_time 排序。
        # 原来写的 post_id 在这个查询里**从来不出现**（它在旧唯一约束里的作用是
        # "同一用户对同一帖子的通知去重"，改成索引后这个语义已经没了），换成 is_read 才有用。
        Index("idx_notification_recipient_post", "recipient_uid", "is_read", "created_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="通知id")
    recipient_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid", ondelete="CASCADE"), nullable=False, comment="接收者uid"
    )
    sender_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid", ondelete="CASCADE"), nullable=True, default=None, comment="触发者uid（系统通知可为空）"
    )
    notif_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="通知类型: reply / like / system"
    )
    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True, default=None, comment="相关帖子id"
    )
    content: Mapped[str] = mapped_column(Text, nullable=True, default="", comment="通知内容")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已读")
    read_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=None, comment="阅读时间"
    )
