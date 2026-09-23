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
    # ## 为什么补上 created_time 和 author_uid（2026-09-23）
    # 和白名单模型那批同款的"静默失效"——**response_model 只输出这里声明过的字段**，
    # ORM 对象上有的东西只要没登记就会被悄悄滤掉，不报错、不警告。
    # 这两处都是前端在用、但模型里漏了的：
    #   - created_time：GoodsDetailView 显示"发布时间"，
    #     以及 `v-if="goods.update_time !== goods.created_time"` 判断这个商品改过没有。
    #     漏了之后 created_time 是 undefined，那个判断恒为 true → 没编辑过的商品也永远显示"编辑于"。
    #   - author_uid：GoodsDetailView 用它判断"我是不是这个商品的作者"
    #     （决定要不要显示编辑/删除按钮）。漏了之后普通作者**看不到自己商品的编辑按钮**，
    #     只有管理员还能操作——因为管理员那条分支走的是 is_superuser。
    # 注意 PostOut 里这两个字段本来就有（author_uid / created_time），
    # 所以这不是"该不该暴露"的取舍问题，是同一条约定在 goods 这边漏执行了。
    created_time: datetime
    update_time: datetime
    author_uid: str
    classify_rel: GoodsClassifyOut
    author: UserBriefOut