from typing import Optional

from pydantic import BaseModel


class CommentsCreateModel(BaseModel):
    content: str
    parent_id: Optional[int] = None  # 楼中楼回复时指定父评论id
