from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.model_base import Base


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (
        UniqueConstraint("post_id", "user_uid", name="uq_user_post_like"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="点赞id")
    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, comment="帖子id"
    )
    user_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid", ondelete="CASCADE"), nullable=False, comment="点赞用户uid"
    )
