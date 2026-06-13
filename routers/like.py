from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from crud.like import LikeService
from schemas.like import LikeActionModel
from tools.dependencies import AccessTokenBearer

router = APIRouter(prefix="/api/likes", tags=["点赞管理"])

like_service = LikeService()
access_token_bearer = AccessTokenBearer()


@router.post("/toggle")
async def toggle_like(
        like_data: LikeActionModel,
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """点赞/取消点赞帖子"""
    result = await like_service.crud_toggle_like(db, like_data.post_id, user_details["user"]["user_uid"])
    return {"code": 200, "message": result["message"], "data": {"liked": result["liked"]}}


@router.get("/count/{post_id}")
async def get_like_count(
        post_id: int,
        db: AsyncSession = Depends(get_database),
):
    """获取帖子点赞数（公开）"""
    count = await like_service.crud_get_like_count(db, post_id)
    return {"code": 200, "message": "获取成功", "data": {"count": count}}


@router.get("/check/{post_id}")
async def check_user_liked(
        post_id: int,
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """检查当前用户是否已点赞"""
    liked = await like_service.crud_check_user_liked(db, post_id, user_details["user"]["user_uid"])
    return {"code": 200, "message": "获取成功", "data": {"liked": liked}}
