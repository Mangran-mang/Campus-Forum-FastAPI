from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict


class UserCreateModel(BaseModel):
    email:EmailStr
    password:str
    username: Optional[str] = None
    nickname: Optional[str] = None
    # avatar_url: Optional[str] = None
    gender: Optional[str] = "未知"
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserUpdateModel(BaseModel):
    email: EmailStr
    password: str = None
    username: str = None
    nickname: str = None
    # avatar_url: str = None
    gender: str = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserLoginModel(BaseModel):
    email: EmailStr
    password: str

class UserOutModel(BaseModel):
    ## 对外输出的用户信息白名单，password 永远不进这个模型
    model_config = ConfigDict(from_attributes=True)  # 允许直接从 ORM 对象读取属性

    uid: str
    email: str
    is_superuser: bool  # 再按前端需要补：昵称、头像、experience、level 等