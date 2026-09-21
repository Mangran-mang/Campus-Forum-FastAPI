from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from crud.bookmark import BookmarkService
from schemas.bookmark import BookmarkActionModel, BookmarkOut, BookmarkToggleOut
from schemas.common import Envelope
from tools.dependencies import AccessTokenBearer
from tools.exceptions import success_response

router = APIRouter(prefix="/api/bookmarks", tags=["收藏管理"])

bookmark_service = BookmarkService()
access_token_bearer = AccessTokenBearer()


@router.post("/toggle", response_model=Envelope[BookmarkToggleOut])
async def toggle_bookmark(
        bookmark_data: BookmarkActionModel,
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """收藏/取消收藏帖子"""
    result = await bookmark_service.crud_toggle_bookmark(db, bookmark_data.post_id, user_details["user"]["user_uid"])
    return success_response(
        data={"bookmarked": result["bookmarked"]}, message=result["message"], )


@router.get("/my", response_model=Envelope[list[BookmarkOut]])
async def get_my_bookmarks(
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """获取我的收藏列表

    ## comment
    只返回收藏记录本身（含 post_id）。前端 PostDetailView 仅用它判断
    "当前帖子有没有被收藏"：res.data.some(b => b.post_id === postId)。
    所以这里不需要把帖子内容带出来。
    """
    bookmarks = await bookmark_service.crud_get_user_bookmarks(db, user_details["user"]["user_uid"])
    return success_response(data=bookmarks, message="获取成功")
