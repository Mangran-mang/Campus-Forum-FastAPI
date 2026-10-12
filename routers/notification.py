from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from crud.notification import NotificationService
from schemas.common import Envelope
from schemas.notification import (
    ClearReadOut,
    NotificationCreateModel,
    NotificationOut,
    NotificationPageOut,
    UnreadCountOut,
)
from tools.dependencies import AccessTokenBearer, UserChecker
from tools.exceptions import success_response

router = APIRouter(prefix="/api/notifications", tags=["通知管理"])

notification_service = NotificationService()
access_token_bearer = AccessTokenBearer()
superuser_checker = UserChecker(True)


@router.get("/", response_model=Envelope[NotificationPageOut])
async def get_notifications(
        db: AsyncSession = Depends(get_database),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=50),
        unread_only: bool = Query(default=False),
        user_details=Depends(access_token_bearer),
):
    """获取当前用户的通知列表"""
    user_uid = user_details["user"]["user_uid"]
    total, notifications = await notification_service.crud_get_user_notifications(
        db, user_uid, page, page_size, unread_only
    )
    return success_response(
        data={"total": total, "notifications": notifications}, message="获取成功", )


@router.get("/unread_count", response_model=Envelope[UnreadCountOut])
async def get_unread_count(
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """获取未读通知数"""
    count = await notification_service.crud_get_unread_count(db, user_details["user"]["user_uid"])
    return success_response(data={"unread_count": count}, message="获取成功")


@router.post("/read/{notif_id}", response_model=Envelope[None])
async def mark_as_read(
        notif_id: int,
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """标记单条通知为已读

    没有数据可返回，data 是 None —— Envelope[None] 正好表达"这里不该有 data"。
    """
    await notification_service.crud_mark_as_read(db, notif_id, user_details["user"]["user_uid"])
    return success_response(message="标记成功")


@router.post("/read_all", response_model=Envelope[None])
async def mark_all_as_read(
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """标记所有通知为已读"""
    await notification_service.crud_mark_all_as_read(db, user_details["user"]["user_uid"])
    return success_response(message="全部标记已读")


@router.post("/clear_read", response_model=Envelope[ClearReadOut])
async def clear_read_notifications(
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """
    清空自己的**已读**通知（未读一条不动）

    ## 为什么用 POST 而不是 DELETE
    与同组的 `/read_all` 保持一致 —— 这个路由组里"改变通知状态"的动作都走 POST。
    REST 上 DELETE 更贴切，但一致性比纯度重要（前端和后来者只看这一组就能摸清规律）。

    ## 为什么不做"清空全部"
    见 crud_clear_read 的注释：未读是用户还没看到的信息，替他删掉会有
    "我明明收到过通知"的困惑。要清未读，先标记已读即可。
    """
    deleted = await notification_service.crud_clear_read(db, user_details["user"]["user_uid"])
    return success_response(data={"deleted": deleted}, message=f"已清理 {deleted} 条已读通知")


@router.post("/send", response_model=Envelope[NotificationOut])
async def send_system_notification(
        notif_data: NotificationCreateModel,
        db: AsyncSession = Depends(get_database),
        _=Depends(superuser_checker),  # 仅管理员
):
    """发送系统通知（仅管理员）"""
    notif = await notification_service.crud_add_notification(db, notif_data.model_dump())
    return success_response(data=notif, message="发送成功")
