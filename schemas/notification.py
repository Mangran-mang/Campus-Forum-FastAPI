from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NotificationCreateModel(BaseModel):
    """系统通知创建"""
    recipient_uid: str
    notif_type: str  # system
    content: str
    post_id: Optional[int] = None


# ============ 输出模型（白名单）============

class NotificationOut(BaseModel):
    """单条通知输出

    ## comment
    ### 为什么没有 sender 的昵称
    Notification 模型上【没有任何 relationship】（sender_uid 只是个字符串外键），
    所以这里只能给出 sender_uid。前端若要显示"谁给你点了赞"，
    需要在 crud 里额外查一次 User 并把它挂到对象上，那时启用下面那行。
    ⚠️ 挂的属性名要注意两点（都是实测踩过的）：
      1. 不能用 `_sender` 这种下划线名去对应 `_sender` 字段——
         Pydantic v2 把 `_xxx` 当私有属性，字段会静默不进输出
      2. 正确做法是：crud 挂 `sender`，或者这里用
         `validation_alias=AliasChoices("sender", "_sender")` 兼容两种
    参考 schemas/message.py 的 ConversationOut 就是这么写的。
    ### read_time 可空
    ORM 里 read_time nullable=True，未读时是 None，所以要 Optional。
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_uid: str
    sender_uid: Optional[str] = None
    notif_type: str
    post_id: Optional[int] = None
    # ## 为什么要有这一行
    # 商品类通知（如 goods_reserve）靠它定位商品/会话。**模型上加了字段不等于能出网** ——
    # response_model 是输出白名单，这里漏声明，前端拿到的就是 undefined（静默丢失，不报错）。
    goods_id: Optional[str] = None
    content: Optional[str] = None
    is_read: bool
    read_time: Optional[datetime] = None
    created_time: datetime
    # sender: Optional[UserBriefOut] = Field(
    #     default=None,
    #     validation_alias=AliasChoices("sender", "_sender"),
    # )


class NotificationPageOut(BaseModel):
    """通知列表的 data 形状：{total, notifications}

    ## comment
    ### 为什么不用 schemas/common.py 的 PageOut
    PageOut 的字段是 {total, items}，而本接口现在返回的键是 notifications。
    改键名要同步改前端，所以先按现有形状定一个模块内的分页模型。
    以后若统一成全站 {total, items}，直接换成 Envelope[PageOut[NotificationOut]] 即可。
    """
    total: int
    notifications: list[NotificationOut]


class UnreadCountOut(BaseModel):
    """未读数的 data 形状：{unread_count}"""
    unread_count: int


class ClearReadOut(BaseModel):
    """清空已读的 data 形状：{deleted}

    给具体条数而不是笼统的"成功" —— 二次确认后的反馈要能让用户确认
    这次操作到底做了什么（真清了 3 条，还是一条都没有）。
    """
    deleted: int
