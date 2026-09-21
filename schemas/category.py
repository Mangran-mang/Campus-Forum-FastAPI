from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


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


# ========== 输出模型（白名单）==========

class CategoryOut(BaseModel):
    """板块输出：帖子列表/详情里嵌的 category 用它

    ## comment
    ### 为什么不带 posts 列表
    Category 上确实有 posts 关系，但这里是"板块的选择项/归属信息"，
    带上它就要额外预加载整张表，还会造成循环引用（PostOut → CategoryOut → PostOut）。
    需要"板块下有哪些帖子"的场景，用 /get_posts?category_id= 单独查。
    ### sort_order
    前端做板块排序要用，所以要暴露。
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int
