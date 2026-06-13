from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from crud.notification import NotificationService
from schemas.notification import NotificationCreateModel
from tools.dependencies import AccessTokenBearer, UserChecker

router = APIRouter(prefix="/api/notifications", tags=["通知管理"])

notification_service = NotificationService()
access_token_bearer = AccessTokenBearer()
superuser_checker = UserChecker(True)


@router.get("/")
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
    return {"code": 200, "message": "获取成功", "data": {"total": total, "notifications": notifications}}


@router.get("/unread_count")
async def get_unread_count(
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """获取未读通知数"""
    count = await notification_service.crud_get_unread_count(db, user_details["user"]["user_uid"])
    return {"code": 200, "message": "获取成功", "data": {"unread_count": count}}


@router.post("/read/{notif_id}")
async def mark_as_read(
        notif_id: int,
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """标记单条通知为已读"""
    await notification_service.crud_mark_as_read(db, notif_id, user_details["user"]["user_uid"])
    return {"code": 200, "message": "标记成功"}


@router.post("/read_all")
async def mark_all_as_read(
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """标记所有通知为已读"""
    await notification_service.crud_mark_all_as_read(db, user_details["user"]["user_uid"])
    return {"code": 200, "message": "全部标记已读"}


@router.post("/send")
async def send_system_notification(
        notif_data: NotificationCreateModel,
        db: AsyncSession = Depends(get_database),
        _=Depends(superuser_checker),  # 仅管理员
):
    """发送系统通知（仅管理员）"""
    notif = await notification_service.crud_add_notification(db, notif_data.model_dump())
    return {"code": 200, "message": "发送成功", "data": notif}
