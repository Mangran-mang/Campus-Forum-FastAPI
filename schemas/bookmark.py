from pydantic import BaseModel


class BookmarkActionModel(BaseModel):
    post_id: int
