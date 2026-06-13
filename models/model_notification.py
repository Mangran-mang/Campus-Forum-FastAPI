from datetime import datetime

from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.model_base import Base


class Notification(Base):
    __tablename__ = "notifications"

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
