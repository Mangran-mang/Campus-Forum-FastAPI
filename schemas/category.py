from typing import Optional

from pydantic import BaseModel


class CategoryCreateModel(BaseModel):
    name: str
    description: Optional[str] = ""
    icon: Optional[str] = ""
    sort_order: Optional[int] = 0


class CategoryUpdateModel(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
