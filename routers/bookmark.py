from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from crud.bookmark import BookmarkService
from schemas.bookmark import BookmarkActionModel
from tools.dependencies import AccessTokenBearer

router = APIRouter(prefix="/api/bookmarks", tags=["收藏管理"])

bookmark_service = BookmarkService()
access_token_bearer = AccessTokenBearer()


@router.post("/toggle")
async def toggle_bookmark(
        bookmark_data: BookmarkActionModel,
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """收藏/取消收藏帖子"""
    result = await bookmark_service.crud_toggle_bookmark(db, bookmark_data.post_id, user_details["user"]["user_uid"])
    return {"code": 200, "message": result["message"], "data": {"bookmarked": result["bookmarked"]}}


@router.get("/my")
async def get_my_bookmarks(
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """获取我的收藏列表"""
    bookmarks = await bookmark_service.crud_get_user_bookmarks(db, user_details["user"]["user_uid"])
    return {"code": 200, "message": "获取成功", "data": bookmarks}
