from pydantic import BaseModel, Field


class MessageCreateModel(BaseModel):
    """发送消息的请求体"""
    content: str = Field(..., min_length=1, max_length=2000, description="消息内容")


class ConversationCreateModel(BaseModel):
    """创建会话请求体（传对方 uid 即可）"""
    other_uid: str = Field(..., min_length=1, max_length=36, description="对方用户uid")
