# 后台管理模块的 schema
"""
后台管理的输出模型
"""
from pydantic import BaseModel

from schemas.goods import GoodsOutModel
from schemas.posts import PostOut
from schemas.user import UserOutModel


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
    total:int
    page:int
    page_size:int


