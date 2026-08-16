from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.model_base import Base


class GoodsComment(Base):
    __tablename__ = "goods_comment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="评论id")
    content: Mapped[str] = mapped_column(String(255), nullable=False, comment="评论内容")
    goods_gid: Mapped[str] = mapped_column(
        String(36), ForeignKey("goods.gid", ondelete="CASCADE"), nullable=False, comment="商品id"
    )
    author_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid", onupdate="CASCADE"), nullable=False, comment="作者id"
    )
    parent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("goods_comment.id", ondelete="CASCADE"), nullable=True, default=None, comment="父评论id（支持楼中楼）"
    )

    # 关系映射
    author: Mapped["User"] = relationship("User", back_populates="goods_comments")
    parent: Mapped["GoodsComment"] = relationship("GoodsComment", remote_side="GoodsComment.id", back_populates="replies")
    replies: Mapped[list["GoodsComment"]] = relationship("GoodsComment", back_populates="parent")
