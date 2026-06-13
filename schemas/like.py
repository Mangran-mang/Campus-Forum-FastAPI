from pydantic import BaseModel


class LikeActionModel(BaseModel):
    post_id: int
