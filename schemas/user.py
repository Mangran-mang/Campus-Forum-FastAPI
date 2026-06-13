from typing import Optional

from pydantic import BaseModel

class UserCreateModel(BaseModel):
    email:str
    password:str
    username: Optional[str] = None
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    gender: Optional[str] = "未知"
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserUpdateModel(BaseModel):
    email: str
    password: str = None
    username: str = None
    nickname: str = None
    avatar_url: str = None
    gender: str = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserLoginModel(BaseModel):
    email: str
    password: str