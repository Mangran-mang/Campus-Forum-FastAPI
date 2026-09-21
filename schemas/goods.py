from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from schemas.user import UserBriefOut


class GoodsCreatePyModel(BaseModel):
    name: str
    classify: str
    status: str
    price: float

class GoodsUpdatePyModel(BaseModel):
    name: str
    classify: str
    status: str
    price: float

# ========== 新增：对外输出模型（白名单） ==========

# GoodsAuthorOut 已删除：它（uid/nickname/level）与 schemas/user.py 的 UserBriefOut 完全重复。
# 按"字段判据是否真有分叉"的原则——商品作者和帖子作者要暴露的东西是一样的，
# 所以共用 UserBriefOut，不再各写一份（否则以后改 User 的可见字段要改好几处）。


class GoodsClassifyOut(BaseModel):
    """商品分类的精简输出"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class GoodsOutModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gid: str
    name: str
    price: float
    status: str
    update_time: datetime
    classify_rel: GoodsClassifyOut
    author: UserBriefOut