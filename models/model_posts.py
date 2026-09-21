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
        # ## 为什么加 ondelete="CASCADE"（2026-09-21）
        # 不加的话 MySQL 默认是 NO ACTION → 有帖子的用户根本删不掉（DELETE 会 500）。
        # 加了之后：删用户时，他的帖子跟着一起删。
        # ⚠️ 已知并接受的连锁反应：
        #    帖子被删 → comments.post_id 也是 CASCADE → 【帖子下别人的评论也一起没】。
        #    也就是说"删一个用户"会顺带抹掉别人在他帖子下的发言。
        #    这是方案 A（硬删除）的本质代价，不是 bug。
        ForeignKey("user.uid", onupdate="CASCADE", ondelete="CASCADE"),
        nullable= False,
        comment="作者id"
    )
    updated_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        # ## 为什么这里【不能】加 onupdate（实测确认的坑）
        # onupdate 的语义是"这一行只要发生 UPDATE 就触发"，不是"只有编辑才触发"。
        # 而 get_post_by_id 每次浏览都会写一次 view_count：
        #     post.view_count = (post.view_count or 0) + 1
        #     await db.commit()
        # 于是 updated_time 被"浏览"不断刷新，变成"最后被浏览时间"而非"最后编辑时间"。
        # 实测：只改 view_count，updated_time 也会跟着变。
        # 所以编辑时间由 crud_update_post 显式赋值维护（见 crud/posts.py 的手动记录编辑时间）。
        comment="最后编辑时间（业务代码手动赋值，不用 onupdate）"
    )
    author:Mapped["User"] = relationship("User",back_populates="posts")
    category: Mapped["Category"] = relationship("Category", back_populates="posts")