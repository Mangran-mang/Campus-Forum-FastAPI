# 后台管理模块的 schema
"""
后台管理的输出模型
"""
from pydantic import BaseModel

from schemas.goods import GoodsOutModel
from schemas.posts import PostOut
from schemas.user import UserOutModel, LoginUserOut


class AdminUserOut(UserOutModel):
    post_count: int = 0
    comment_count: int = 0
    goods_count: int = 0

class AdminPostOut(PostOut):
    comment_count: int = 0
    like_count: int = 0

class AdminGoodsOut(GoodsOutModel):
    # 直接复用GoodsOutModel其他的以后再说
    pass

class AdminUserPageOut(BaseModel):
    users:list[AdminUserOut]
    total:int
    page:int
    page_size:int

class AdminPostsPageOut(BaseModel):
    posts:list[AdminPostOut]
    total:int
    page:int
    page_size:int

class AdminGoodsPageOut(BaseModel):
    goods:list[GoodsOutModel]
    total: int
    page: int
    page_size: int

class AdminLoginOut(BaseModel):
    access_token: str
    user: LoginUserOut

class AdminOverviewOut(BaseModel):
    """GET /api/admin/overview 的 data 形状

    ## 字段名必须与 crud.get_overview 返回的 dict 键逐一对齐
    crud 返回 dict(row._mapping)，键来自 select(...).label("xxx")，
    response_model 校验的是整个信封 —— 键名对不上就是 500，不是静默丢数据。

    ## 为什么是 user_total / user_today 这种前缀式命名
    按实体分组，前端卡片一行一个实体（每个实体读 total + today 两个数），
    比 total_user / new_user 这种混排更好对应。
    """
    user_total: int
    user_today: int
    post_total: int
    post_today: int
    goods_total: int
    goods_today: int

# schemas/admin.py
class AdminTrendsOut(BaseModel):
    """列式返回：dates 喂 ECharts 的 xAxis，posts 喂 series.data，前端零转换"""
    dates: list[str]
    posts: list[int]

class DistItemOut(BaseModel):
    name: str
    count: int

class AdminDistributionOut(BaseModel):
    post_categories: list[DistItemOut]
    goods_classifies: list[DistItemOut]

class AdminActivityOut(BaseModel):
    dates: list[str]
    uv: list[int]
