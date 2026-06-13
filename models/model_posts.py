from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey, Text, Boolean, \
    func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.model_base import Base

class Posts(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True,comment="帖子id")
    title: Mapped[str] = mapped_column(String(255),nullable= False,comment="帖子标题")
    content: Mapped[str] = mapped_column(Text,nullable= False,comment="帖子内容")
    summary: Mapped[str] = mapped_column(String(255),nullable= True,default="无",comment="帖子摘要")
    view_count: Mapped[int] = mapped_column(Integer,default=1,comment="浏览量")
    is_public: Mapped[bool] = mapped_column(Boolean,default=True,comment="是否公开")
    is_top: Mapped[bool] = mapped_column(Boolean,default=False,comment="是否置顶")
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        comment="板块id"
    )
    author_uid: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.uid",onupdate="CASCADE"),
        nullable= False,
        comment="作者id"
    )
    updated_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间"
    )
    author:Mapped["User"] = relationship("User",back_populates="posts")
    category: Mapped["Category"] = relationship("Category", back_populates="posts")