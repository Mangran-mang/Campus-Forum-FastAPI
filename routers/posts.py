import asyncio
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
from schemas.common import Envelope
from schemas.posts import (
    PostsCreateModel,
    PostsUpdateModel,
    PostOut,
    PostTopModel,
    ReviewResultOut,
)

from tools.dependencies import AccessTokenBearer, UserChecker, get_user_by_token
from tools.exceptions import success_response, APIException, PostException

router = APIRouter(prefix="/api/posts",tags=["帖子管理"])

postservice = PostService()
userservice = UserService()
notificationservice = NotificationService()
access_token_bearer = AccessTokenBearer()
superuser_checker = UserChecker(True)   # 仅管理员

@router.post("/add_post", response_model=Envelope[PostOut])
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
    return success_response(data=post, message="添加成功")

@router.get("/get_posts",response_model=Envelope[list[PostOut]], description="获取帖子列表")
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
    return success_response(data=post_list, message="获取成功")

@router.get("/get_post/{post_id}", response_model=Envelope[PostOut], description="获取帖子详情")
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
    return success_response(data=post, message="获取成功")

@router.post("/update_post", response_model=Envelope[PostOut])
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
    return success_response(data=post, message="更新成功")

@router.delete("/delete_post/{post_id}", response_model=Envelope[bool])
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
    return success_response(data=post, message="删除成功")

@router.post("/admin/set_top/{post_id}", response_model=Envelope[PostOut])
async def set_post_top(
        post_id: int,
        top_data: PostTopModel,
        db: AsyncSession = Depends(get_database),
        _=Depends(superuser_checker),          # ← 仅管理员
):
    """
    置顶 / 取消置顶帖子（仅管理员）

    ## comment
    ### 为什么单独开一个接口，而不是让 /update_post 顺手带上 is_top
    置顶是【管理动作】，和"改帖子内容"不是一回事：
      - /update_post 的调用方是【作者本人】
      - 这个接口的调用方是【管理员】
    混在一起就得在 /update_post 里加"如果传了 is_top 就检查是不是管理员"这类条件，
    以后每加一个管理属性都得再加一次判断 —— 迟早漏一个。
    分开之后，权限边界就是"这个接口有没有挂 UserChecker"，扫一眼就能看出来。
    ### 为什么不额外校验"不能置顶私密帖子"
    置顶只影响排序，不影响可见性。私密帖子本来就只有作者能看见，
    把它置顶也不会泄露给任何人，所以不需要额外校验。
    ### 为什么用 request body 传 is_top 而不是 query 参数
    保持一致：改状态的接口都用 body。query 参数留在路由 path 里（post_id）。
    """
    post = await postservice.crud_set_post_top(db, post_id, top_data.is_top)
    return success_response(
        data=post,
        message="已置顶" if top_data.is_top else "已取消置顶",
    )


@router.post("/report/{post_id}", response_model=Envelope[ReviewResultOut])
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
    # 这三处原来是 return {"code": 404/400, ...}，HTTP 状态却是 200，
    # 前端只能读 body 才知道失败。改成 raise 后状态码和 body 一致，
    # 统一由全局异常处理器转成 {code, message, data}
    post = await postservice.crud_get_post_details_by_id(db, post_id, reporter_uid)
    if not post:
        raise PostException("帖子不存在")

    # 不能举报自己的帖子
    if post.author_uid == reporter_uid:
        raise APIException("不能举报自己的帖子")  # APIException 默认 400

    # Redis 去重：24 小时内同一用户不能重复举报同一帖子
    if not await try_report_deduplicate(post_id, reporter_uid):
        raise APIException("你已举报过该帖子，请勿重复举报")

    reporter_name = user_details["user"].get("user_nickname") or user_details["user"].get("user_email")

    # 调用 AI 审核（同步，qwen3.6-flash 约 2-5 秒）
    try:
        review_result = await asyncio.to_thread(review_post_content, post.title, post.content)# 遗留问题5
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
        return success_response(
            message="举报已受理，AI 审核暂时不可用，已转交管理员处理", )

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
        return success_response(
            data=review_result,
            message=f"AI 审核判定违规（{viol_type}），帖子已删除", )

    # 未违规：保留帖子，通知举报人
    await notificationservice.crud_add_notification(db, {
        "recipient_uid": reporter_uid,
        "sender_uid": post.author_uid,
        "notif_type": "report",
        "post_id": post_id,
        "content": f"你举报的帖子「{post.title}」经 AI 审核未发现违规内容，帖子已保留",
    })
    return success_response(
        data=review_result, message="AI 审核未发现违规内容，帖子已保留", )