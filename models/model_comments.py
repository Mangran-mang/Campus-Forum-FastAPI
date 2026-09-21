from sqlalchemy import Integer, String, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.model_base import Base


class Comments(Base):
    __tablename__ = "comments"
    __table_args__ = (
        # ⚠️ 这里的尾逗号不能省！
        # 少了它，括号里就只剩一个 Index 对象（不是 tuple），
        # SQLAlchemy 会直接抛 ArgumentError: __table_args__ value must be a tuple, dict, or None
        # —— 而且是 import 阶段就炸，整个项目起不来。
        # 单元素的元组在 Python 里必须靠这个逗号才能成立，这是语法层面的坑，不是 SQLAlchemy 的。
        Index("ix_comments_post_parent_time", "post_id", "parent_id", "created_time"),
    )


    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True,comment="评论id")
    content: Mapped[str] = mapped_column(String(255), nullable=False, comment="评论内容")
    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, comment="帖子id"
    )
    author_uid: Mapped[str] = mapped_column(
        # ## 为什么加 ondelete="CASCADE"（2026-09-21）
        # 不加的话 MySQL 默认 NO ACTION → 评论过东西的用户删不掉（DELETE 会 500）。
        # 加了之后：删用户时，他发过的评论跟着一起删。
        # （注意方向：这里管的是"评论的作者被删"。评论所【属于的帖子】被删，
        #   走的是下面 post_id 那条 CASCADE。）
        String(36), ForeignKey("user.uid", onupdate="CASCADE", ondelete="CASCADE"), nullable=False, comment="作者id"
    )
    parent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, default=None, comment="父评论id（支持楼中楼）"
    )

    # 关系映射
    author: Mapped["User"] = relationship("User", back_populates="comments")
    parent: Mapped["Comments"] = relationship("Comments", remote_side="Comments.id", back_populates="replies")
    replies: Mapped[list["Comments"]] = relationship("Comments", back_populates="parent")
