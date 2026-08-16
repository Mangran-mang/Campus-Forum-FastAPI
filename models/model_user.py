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
    token: Mapped["Token"] = relationship("Token",back_populates="user",uselist= False)
    comments: Mapped[list["Comments"]] = relationship("Comments", back_populates="author")
    goods: Mapped[list["Goods"]] = relationship("Goods", back_populates="author")
    goods_comments: Mapped[list["GoodsComment"]] = relationship("GoodsComment", back_populates="author")
    images: Mapped[list["Image"]] = relationship("Image", back_populates="author")
    # 私信关系（按在会话中的角色分两个方向）
    conversations_as_a: Mapped[list["Conversation"]] = relationship(
        "Conversation", foreign_keys="Conversation.user_a_uid", back_populates="user_a"
    )
    conversations_as_b: Mapped[list["Conversation"]] = relationship(
        "Conversation", foreign_keys="Conversation.user_b_uid", back_populates="user_b"
    )
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="sender")