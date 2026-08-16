import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ai_agent.review import review_post_content
from config.database_config import get_database
from config.redis_config import try_report_deduplicate
from crud.notification import NotificationService
from crud.posts import PostService
from crud.user import UserService
from models import User, Notification
from schemas.posts import PostsCreateModel, PostsUpdateModel

from tools.dependencies import AccessTokenBearer,get_user_by_token

router = APIRouter(prefix="/api/posts",tags=["帖子管理"])

postservice = PostService()
userservice = UserService()
notificationservice = NotificationService()
access_token_bearer = AccessTokenBearer()

@router.post("/add_post")
async def add_new_post(
        post_data:PostsCreateModel,
        db:AsyncSession=Depends(get_database),
        user_details = Depends(access_token_bearer)
):
    """
    添加帖子（作者 uid 由 token 自动填充）
    """
    post_data.author_uid = user_details["user"]["user_uid"]
    post = await postservice.crud_add_new_post(db,post_data)
    return {"code":200,"message":"添加成功","data":post}

@router.get("/get_posts")
async def get_posts_list(
        db:AsyncSession=Depends(get_database),
        page:int=Query(default=1,alias="page",description="页码",ge=1),
        page_size:int=Query(default=10,alias="page_size",description="每页数量",ge=1),
        author_uid:str=None,
        category_id:int=None,
        user_details = Depends(access_token_bearer)# 1是强制要求登录2是拿到用户详情
):
    """
    获取帖子列表
    author_uid：指定要查的作者的uid
    category_id：指定板块id
    user_details：解码后的token详情，里面有email和uid
    """
    total,post_list = await postservice.crud_get_posts_list(
        db,
        page,
        page_size,
        author_uid,
        category_id,
        user_details["user"]["user_uid"]
    )
    has_more = total > page * page_size# 暂未用到
    return {"code":200,"message":"获取成功","data":post_list}

@router.get("/get_post/{post_id}")
async def get_post_by_id(
        post_id:int,
        db:AsyncSession=Depends(get_database),
        user_details = Depends(access_token_bearer)
):
    """
    通过id获取帖子
    原本我以为它只是查帖子而已，但在实际运行中
    它就是查看帖子，所以浏览量也应该加一
    """
    current_user_uid = user_details["user"]["user_uid"]
    post = await postservice.crud_get_post_details_by_id(db,post_id,current_user_uid)
    # 浏览量 +1
    post.view_count = (post.view_count or 0) + 1
    await db.commit()
    await db.refresh(post, ["author", "category"])
    return {"code":200,"message":"获取成功","data":post}

@router.post("/update_post")
async def update_post(
        post_data:PostsUpdateModel,
        db:AsyncSession=Depends(get_database),
        user_details = Depends(access_token_bearer),
        post_id:int=Query(...,description="帖子id")
):
    """
    更新帖子
    """
    orm_user:User = await get_user_by_token(token_details=user_details,db=db)
    post = await postservice.crud_update_post(db,post_id,post_data,orm_user)
    return {"code":200,"message":"更新成功","data":post}

@router.delete("/delete_post/{post_id}")
async def delete_post(
        post_id:int,
        db:AsyncSession=Depends(get_database),
        user_details = Depends(access_token_bearer),
):
    """
    删除帖子
    """
    orm_user:User = await get_user_by_token(token_details=user_details,db=db)
    post = await postservice.crud_delete_post(db,post_id,orm_user)
    return {"code":200,"message":"删除成功","data":post}

@router.post("/report/{post_id}")
async def report_post(
        post_id: int,
        db: AsyncSession = Depends(get_database),
        user_details = Depends(access_token_bearer),
):
    """
    举报帖子：由 AI 审核帖子内容（只看贴主发布的标题与正文，不看评论）
    判定违规则硬删帖子并通知双方，未违规则保留并通知举报人
    """
    reporter_uid = user_details["user"]["user_uid"]
    # 获取被举报的帖子
    post = await postservice.crud_get_post_details_by_id(db, post_id, reporter_uid)
    if not post:
        return {"code": 404, "message": "帖子不存在"}

    # 不能举报自己的帖子
    if post.author_uid == reporter_uid:
        return {"code": 400, "message": "不能举报自己的帖子"}

    # Redis 去重：24 小时内同一用户不能重复举报同一帖子
    if not await try_report_deduplicate(post_id, reporter_uid):
        return {"code": 400, "message": "你已举报过该帖子，请勿重复举报"}

    reporter_name = user_details["user"].get("user_nickname") or user_details["user"].get("user_email")

    # 调用 AI 审核（同步，qwen3.6-flash 约 2-5 秒）
    try:
        review_result = review_post_content(post.title, post.content)
        violated = review_result.get("violated", False)
        viol_type = review_result.get("type", "")
        reason = review_result.get("reason", "")
    except Exception as e:
        # AI 审核失败：降级为通知管理员人工审核，保证举报功能可用
        logging.exception("AI 审核调用失败，降级为人工审核")
        superusers = await userservice.crud_get_superusers(db)
        if superusers:
            notif_list = [
                {
                    "recipient_uid": admin.uid,
                    "sender_uid": reporter_uid,
                    "notif_type": "report",
                    "post_id": post_id,
                    "content": f"用户 {reporter_name} 举报了帖子「{post.title}」，AI 审核暂不可用，需人工处理",
                }
                for admin in superusers
            ]
            await notificationservice.crud_add_notifications(db, notif_list)
        return {"code": 200, "message": "举报已受理，AI 审核暂时不可用，已转交管理员处理"}

    if violated:
        # 违规：硬删帖子（评论经外键 CASCADE 级联删除）
        post_title = post.title
        post_author_uid = post.author_uid
        await db.delete(post)
        await db.commit()
        # 通知双方（post_id 传 None，避免通知随帖子级联删除）
        await notificationservice.crud_add_notification(db, {
            "recipient_uid": post_author_uid,
            "sender_uid": reporter_uid,
            "notif_type": "report",
            "post_id": None,
            "content": f"你的帖子「{post_title}」被举报，经 AI 审核判定违规（{viol_type}：{reason}），已删除",
        })
        await notificationservice.crud_add_notification(db, {
            "recipient_uid": reporter_uid,
            "sender_uid": post_author_uid,
            "notif_type": "report",
            "post_id": None,
            "content": f"你举报的帖子「{post_title}」经 AI 审核确认违规，已删除",
        })
        return {"code": 200, "message": f"AI 审核判定违规（{viol_type}），帖子已删除", "data": review_result}

    # 未违规：保留帖子，通知举报人
    await notificationservice.crud_add_notification(db, {
        "recipient_uid": reporter_uid,
        "sender_uid": post.author_uid,
        "notif_type": "report",
        "post_id": post_id,
        "content": f"你举报的帖子「{post.title}」经 AI 审核未发现违规内容，帖子已保留",
    })
    return {"code": 200, "message": "AI 审核未发现违规内容，帖子已保留", "data": review_result}