from datetime import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from schemas.user import UserBriefOut


# ============ 输入模型 ============
class MessageCreateModel(BaseModel):
    """发送消息的请求体"""
    content: str = Field(..., min_length=1, max_length=2000, description="消息内容")


class ConversationCreateModel(BaseModel):
    """创建会话请求体（传对方 uid 即可）"""
    other_uid: str = Field(..., min_length=1, max_length=36, description="对方用户uid")


# ============ 输出模型（白名单）============

class MessageOut(BaseModel):
    """单条私信输出

    ## comment
    字段与 routers/message.py 原来的 _message_brief() 一一对应，前端零改动。
    挂上 response_model 之后 _message_brief 里那句
    `created_time.isoformat()` 可以删掉——Pydantic 在 JSON 模式下会自动 ISO 化。

    ### sender 必须已在 crud 里加载好
    crud_get_messages 用了 selectinload(Message.sender)、crud_add_message 用了
    refresh(orm_msg, ["sender"])，两者都能直接喂给这个模型。
    漏了的话读 sender 会触发异步懒加载 → MissingGreenlet，
    而不是拿到 null（Optional 的默认值保护不了这种情况）。
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender_uid: str
    content: str
    created_time: datetime
    sender: Optional[UserBriefOut] = None


class ConversationOut(BaseModel):
    """会话输出

    ## comment
    ### other_user 为什么用共享的 UserBriefOut
    它是"对方"，属于"别人看我"——绝不能把 email 带出去。
    这同时修掉了 routers/message.py 里 _user_brief() 泄露 email 的问题
    （那个函数返回 uid/nickname/username/email/level/is_superuser）。

    ### other_user / last_message 的来源与取名
    两者都不是 Conversation 表上的列，是 crud 里临时挂上去的：
      _attach_other_user  → conv._other_user
      _load_last_messages → conv._last_message
    crud 挂的是带下划线的名字，而字段名不能带下划线——
    Pydantic v2 会把 `_xxx` 当私有属性，字段会静默不进输出（实测确认）。
    所以这里用 validation_alias 同时接受两种名字，crud 不用改：
      对象上是 _other_user  → 取到
      对象上是 other_user   → 取到
      两个都没有            → 默认 None
    （另一种做法是把 crud 里挂的属性名去掉下划线，二选一即可。）

    ### last_message 可为 None
    新会话还没发过消息时为 None，前端要显示"暂无消息"。
    注意 crud_get_or_create_conversation 只挂了 _other_user、没挂 _last_message，
    所以那条路径下 last_message 一定是 None——这符合预期。
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_a_uid: str
    user_b_uid: str
    created_time: datetime
    updated_time: datetime
    other_user: Optional[UserBriefOut] = Field(
        default=None,
        validation_alias=AliasChoices("other_user", "_other_user"),
    )
    last_message: Optional[MessageOut] = Field(
        default=None,
        validation_alias=AliasChoices("last_message", "_last_message"),
    )


# ============ 分页外壳（data 的形状）============

class ConversationPageOut(BaseModel):
    """GET /conversations 的 data 形状：{total, conversations}"""
    total: int
    conversations: list[ConversationOut]


class MessagePageOut(BaseModel):
    """GET /conversations/{id}/messages 的 data 形状：{total, messages, current_uid}

    ## comment
    current_uid 是给前端判断"这条消息是不是我发的"用的，
    前端本来也能从本地登录态拿到，但后端一并返回更省事（保持原样，不改结构）。
    """
    total: int
    messages: list[MessageOut]
    current_uid: str
