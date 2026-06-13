from typing import Optional

from pydantic import BaseModel


class NotificationCreateModel(BaseModel):
    """系统通知创建"""
    recipient_uid: str
    notif_type: str  # system
    content: str
    post_id: Optional[int] = None
