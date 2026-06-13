from typing import Optional

from pydantic import BaseModel


class PostsCreateModel(BaseModel):
    """
    需要标题、内容
    author_uid 由 token 自动填充，前端无需传入
    """
    title: str
    content: str
    summary: Optional[str] = None
    is_public: bool = True
    is_top: bool = False
    category_id: Optional[int] = None
    author_uid: Optional[str] = None  # 由后端从 token 获取

    model_config = {"from_attributes": True}

class PostsUpdateModel(BaseModel):
    """
    需要标题、内容
    """
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    is_public: Optional[bool] = None
    is_top: Optional[bool] = None
    category_id: Optional[int] = None

    model_config = {"from_attributes": True}