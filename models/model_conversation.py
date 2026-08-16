from datetime import datetime

from sqlalchemy import Integer, String, DateTime, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.model_base import Base


class Conversation(Base):
    """
    私信会话表：一个会话 = 两个用户之间的对话
    user_a_uid / user_b_uid 按 uid 升序存储（小的在 a），配合联合唯一约束保证 A-B / B-A 只有一个会话
    """
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("user_a_uid", "user_b_uid", name="uq_conversation_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="会话id")
    user_a_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid", ondelete="CASCADE"), nullable=False, comment="参与者A(uid较小)"
    )
    user_b_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid", ondelete="CASCADE"), nullable=False, comment="参与者B(uid较大)"
    )
    created_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="会话创建时间"
    )
    updated_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="最后消息时间"
    )

    # 关系映射
    user_a: Mapped["User"] = relationship("User", foreign_keys=[user_a_uid], back_populates="conversations_as_a")
    user_b: Mapped["User"] = relationship("User", foreign_keys=[user_b_uid], back_populates="conversations_as_b")
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", order_by="Message.created_time"
    )
