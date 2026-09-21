from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

import uuid
from models.model_base import Base



class User(Base):
    __tablename__ = "user"

    uid: Mapped[str] = mapped_column(String(36),primary_key=True,nullable= False,default=uuid.uuid4,comment="用户id")
    email: Mapped[str] = mapped_column(String(255),unique= True,nullable= False,comment="用户账号")
    password: Mapped[str] = mapped_column(String(255),nullable= False,comment="用户密码")
    username: Mapped[Optional[str]] = mapped_column(String(50),nullable= True,comment="用户名")
    nickname: Mapped[Optional[str]] = mapped_column(String(50),nullable= True,default="无",comment="昵称")
    # avatar_url: Mapped[Optional[str]] = mapped_column(String(255),nullable= True,default="",comment="头像")
    gender: Mapped[str] = mapped_column(Enum('男','女','未知'),nullable= False,comment="性别",default='未知')
    is_active: Mapped[bool] = mapped_column(default=True,comment="是否激活")
    is_superuser: Mapped[bool] = mapped_column(default=False,comment="是否是管理员")
    # 等级系统：经验值与等级（等级由经验推导，0 表示新手/未分级）
    experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="经验值")
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="等级(0=新手,1~10)")

    updated_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间"
    )
    posts: Mapped["list[Posts]"] = relationship("Posts",back_populates="author")
    # ========== 用户与所有子表的关系 ==========
    # ## 为什么每个关系都要加 passive_deletes=True（2026-09-21 实测踩出来的）
    #
    # SQLAlchemy 删父对象时的默认行为【不是】交给数据库级联，而是自己动手：
    # 它会把子集合加载进来，然后对每个子行执行
    #     UPDATE posts SET author_uid = NULL WHERE id = ...
    # 也就是"把外键置空"。而这些列都是 NOT NULL → 直接抛
    #     IntegrityError (1048, "Column 'author_uid' cannot be null")
    # → 接口层表现为 400 / 500。
    #
    # 所以【光把数据库外键改成 ON DELETE CASCADE 是不够的】——
    # ORM 根本不会让那条 CASCADE 生效，它自己先插了一手。
    # passive_deletes=True 的意思是"别管子集合，交给数据库自己处理"，
    # 这时数据库的 ON DELETE CASCADE 才能真正跑起来。
    #
    # （前提：这 9 个关系的对应外键都已在数据库里是 CASCADE，
    #   见迁移 d1e2f3a4b5c6。两边必须成对改，少一边都不行。）
    #
    # 注意：notifications 表没有 User 上的关系（只有两个裸 FK 列），
    # 所以它不经过 ORM，本来就直接由数据库级联处理。
    posts: Mapped["list[Posts]"] = relationship(
        "Posts", back_populates="author", passive_deletes=True
    )
    token: Mapped["Token"] = relationship(
        "Token", back_populates="user", uselist=False, passive_deletes=True
    )
    comments: Mapped[list["Comments"]] = relationship(
        "Comments", back_populates="author", passive_deletes=True
    )
    goods: Mapped[list["Goods"]] = relationship(
        "Goods", back_populates="author", passive_deletes=True
    )
    goods_comments: Mapped[list["GoodsComment"]] = relationship(
        "GoodsComment", back_populates="author", passive_deletes=True
    )
    images: Mapped[list["Image"]] = relationship(
        "Image", back_populates="author", passive_deletes=True
    )
    # 私信关系（按在会话中的角色分两个方向）
    conversations_as_a: Mapped[list["Conversation"]] = relationship(
        "Conversation", foreign_keys="Conversation.user_a_uid",
        back_populates="user_a", passive_deletes=True
    )
    conversations_as_b: Mapped[list["Conversation"]] = relationship(
        "Conversation", foreign_keys="Conversation.user_b_uid",
        back_populates="user_b", passive_deletes=True
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="sender", passive_deletes=True
    )