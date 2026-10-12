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


class GoodsDetailOut(GoodsOutModel):
    """
    商品详情输出 = 列表字段 + 详情专属字段

    ## 为什么单独一个模型，而不是给 GoodsOutModel 加个默认 0 的字段
    reserve_count（"已有 N 人预定"）只有详情页要显示，列表接口不会为它跑那个聚合。
    如果把它挂在共用的 GoodsOutModel 上，列表返回的会是"看起来像真数据的 0"——
    那比缺字段更糟：前端会当真值用，而不是显示 undefined。
    字段的"有没有算"要能从类型上看出来，所以用一个子类把它划出来。
    """
    reserve_count: int = 0


class ReservationItemOut(BaseModel):
    """预定列表项（卖家视角：谁想买我的东西）"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    gid: str
    status: str
    created_time: datetime
    updated_time: datetime
    # 只给 UserBriefOut（uid/nickname/level）—— 刻意不给联系方式：
    # 平台不接支付、不担保，就别顺手把用户的手机号之类也暴露出去。要聊走私信。
    buyer: UserBriefOut


class GoodsReserveOut(BaseModel):
    """
    预定接口的返回：预定记录 + 目标会话 id

    ## 为什么把 conversation_id 一起返回
    买家点"预定购买"的**真实意图是找卖家聊**（平台不接支付，成交靠线下）。
    前端拿到它就能直接跳进会话，不用再调一次"获取或创建会话"的接口。
    """
    reservation_id: int
    status: str
    created_time: datetime
    conversation_id: int
    # true = 之前就预定过（前端提示"你已经预定过了，去私信里继续聊"）
    # 由后端判断，而不是让前端自己比对列表 —— 重复点击的判定标准只应有一处
    already_reserved: bool