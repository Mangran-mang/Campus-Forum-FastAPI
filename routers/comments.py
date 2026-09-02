from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from crud.comments import CommentsService
from crud.notification import NotificationService
from models.model_posts import Posts
from schemas.comments import CommentsCreateModel
from tools.dependencies import AccessTokenBearer,get_user_by_token
from tools.exceptions import success_response

router = APIRouter(prefix="/api/comments",tags=["评论管理"])

commentsservice = CommentsService()
notificationservice = NotificationService()
access_token_bearer = AccessTokenBearer()

@router.post("/addcomment")
async def add_new_comment(
        comment_data:CommentsCreateModel,
        db:AsyncSession=Depends(get_database),
        post_id:int=Query(...,description="帖子id"),
        user_details = Depends(access_token_bearer)
):
    """
    添加评论（含通知触发）
    """
    commenter_uid = user_details["user"]["user_uid"]
    comment = await commentsservice.crud_add_new_comment_into_post(
        db,
        comment_data,
        post_id,
        commenter_uid
    )

    # 查询帖子作者
    stmt = select(Posts).where(Posts.id == post_id)
    result = await db.execute(stmt)
    post = result.scalar_one_or_none()

    if post and post.author_uid != commenter_uid:
        if comment_data.parent_id is not None:
            # 楼中楼回复：通知父评论作者
            parent_comment = await commentsservice.crud_get_comment_by_comment_id(db, comment_data.parent_id)
            if parent_comment and parent_comment.author_uid != commenter_uid:
                await notificationservice.crud_add_notification(db, {
                    "recipient_uid": parent_comment.author_uid,
                    "sender_uid": commenter_uid,
                    "notif_type": "reply",
                    "post_id": post_id,
                    "content": "有人回复了你的评论"
                })
        else:
            # 一级评论：通知帖子作者
            await notificationservice.crud_add_notification(db, {
                "recipient_uid": post.author_uid,
                "sender_uid": commenter_uid,
                "notif_type": "reply",
                "post_id": post_id,
                "content": "有人评论了你的帖子"
            })

    return success_response(data=comment, message="添加成功")

@router.get("/getcomments")
async def get_comments_list(
        post_id:int,
        db:AsyncSession=Depends(get_database),
        page:int=Query(default=1,alias="page",description="页码",ge=1),
        page_size:int=Query(default=10,alias="page_size",description="每页数量",ge=1),
):
    """
    获取评论列表
    """
    total,comments_list = await commentsservice.crud_get_comments_by_post_id(
        db,
        post_id,
        page,
        page_size
    )
    has_more = total > page * page_size# 暂未用到
    return success_response(
        data=comments_list, message=f"成功查询到帖子{post_id}", )

@router.delete("/deletecomment")
async def delete_comment(
        comment_id:int,
        db:AsyncSession=Depends(get_database),
        user_details = Depends(access_token_bearer),
):
    """
    删除评论
    """
    orm_user = await get_user_by_token(token_details=user_details,db=db)
    result = await commentsservice.crud_delete_comment_by_comment_id(
        db,
        comment_id,
        user_details["user"]["user_uid"],
        orm_user
    )
    # 原来把 result 这个 bool 拼进 message（"删除评论状态True"），
    # 现在挪到 data 里，message 只留一句能直接展示的话
    return success_response(data=result, message="删除成功")