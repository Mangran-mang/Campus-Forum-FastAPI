from datetime import datetime

from sqlalchemy import Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.model_base import Base


class Message(Base):
    """私信消息表：会话里的每一条消息"""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="消息id")
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, comment="所属会话id"
    )
    sender_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid", ondelete="CASCADE"), nullable=False, comment="发送者uid"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    created_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="发送时间"
    )

    # 关系映射
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    sender: Mapped["User"] = relationship("User", back_populates="messages")
