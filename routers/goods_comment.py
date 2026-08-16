from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from crud.goods_comment import GoodsCommentService
from crud.notification import NotificationService
from models.model_goods import Goods
from schemas.goods_comment import GoodsCommentCreateModel
from tools.dependencies import AccessTokenBearer, get_user_by_token

router = APIRouter(prefix="/api/goods", tags=["商品评论"])

comment_service = GoodsCommentService()
notification_service = NotificationService()
access_token_bearer = AccessTokenBearer()


@router.post("/{goods_gid}/comments")
async def add_comment(
        goods_gid: str,
        comment_data: GoodsCommentCreateModel,
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """添加商品评论"""
    commenter_uid = user_details["user"]["user_uid"]
    comment = await comment_service.crud_add_comment(
        db, comment_data, goods_gid, commenter_uid
    )

    # 通知商品作者
    stmt = select(Goods).where(Goods.gid == goods_gid)
    result = await db.execute(stmt)
    goods = result.scalar_one_or_none()

    if goods and goods.author_uid != commenter_uid:
        if comment_data.parent_id is not None:
            parent_comment = await comment_service.crud_get_comment_by_id(db, comment_data.parent_id)
            if parent_comment and parent_comment.author_uid != commenter_uid:
                await notification_service.crud_add_notification(db, {
                    "recipient_uid": parent_comment.author_uid,
                    "sender_uid": commenter_uid,
                    "notif_type": "reply",
                    "post_id": None,
                    "content": "有人回复了你的评论",
                })
        else:
            await notification_service.crud_add_notification(db, {
                "recipient_uid": goods.author_uid,
                "sender_uid": commenter_uid,
                "notif_type": "reply",
                "post_id": None,
                "content": "有人评论了你的商品",
            })

    return {"code": 200, "message": "评论成功", "data": comment}


@router.get("/{goods_gid}/comments")
async def get_comments(
        goods_gid: str,
        db: AsyncSession = Depends(get_database),
        page: int = Query(default=1, alias="page", description="页码", ge=1),
        page_size: int = Query(default=10, alias="page_size", description="每页数量", ge=1),
):
    """获取商品评论列表"""
    total, comments_list = await comment_service.crud_get_comments_by_goods(
        db, goods_gid, page, page_size
    )
    return {"code": 200, "message": "获取成功", "data": comments_list, "total": total}


@router.delete("/comments/{comment_id}")
async def delete_comment(
        comment_id: int,
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """删除商品评论"""
    orm_user = await get_user_by_token(token_details=user_details, db=db)
    result = await comment_service.crud_delete_comment(
        db, comment_id, user_details["user"]["user_uid"], orm_user
    )
    return {"code": 200, "message": f"删除状态: {result}"}
