from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String,Enum
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
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255),nullable= True,default="",comment="头像")
    gender: Mapped[str] = mapped_column(Enum('男','女','未知'),nullable= False,comment="性别",default='未知')
    is_active: Mapped[bool] = mapped_column(default=True,comment="是否激活")
    is_superuser: Mapped[bool] = mapped_column(default=False,comment="是否是管理员")

    updated_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间"
    )
    posts: Mapped["Posts"] = relationship("Posts",back_populates="author")
    token: Mapped["Token"] = relationship("Token",back_populates="user",uselist= False)
    comments: Mapped[list["Comments"]] = relationship("Comments", back_populates="author")