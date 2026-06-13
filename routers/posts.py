from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from crud.posts import PostService
from models import User
from schemas.posts import PostsCreateModel, PostsUpdateModel

from tools.dependencies import AccessTokenBearer,get_user_by_token

router = APIRouter(prefix="/api/posts",tags=["帖子管理"])

postservice = PostService()
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
    """
    current_user_uid = user_details["user"]["user_uid"]
    post = await postservice.crud_get_post_details_by_id(db,post_id,current_user_uid)
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