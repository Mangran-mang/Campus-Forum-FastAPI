from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from crud.message import MessageService
from schemas.common import Envelope
from schemas.message import (
    ConversationCreateModel,
    ConversationOut,
    ConversationPageOut,
    MessageCreateModel,
    MessageOut,
    MessagePageOut,
)
from schemas.user import UserBriefOut
from tools.dependencies import AccessTokenBearer
from tools.exceptions import success_response

router = APIRouter(prefix="/api/messages", tags=["私信管理"])

message_service = MessageService()
access_token_bearer = AccessTokenBearer()


@router.post("/conversation", response_model=Envelope[ConversationOut])
async def get_or_create_conversation(
        other_uid: str = Query(..., min_length=1, max_length=36, description="对方用户uid"),
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """获取或创建与某用户的会话（幂等：已存在则直接返回）"""
    current_uid = user_details["user"]["user_uid"]
    conv = await message_service.crud_get_or_create_conversation(db, current_uid, other_uid)
    return success_response(data=conv, message="获取成功")


@router.get("/conversations", response_model=Envelope[ConversationPageOut])
async def get_conversations(
        db: AsyncSession = Depends(get_database),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=50),
        user_details=Depends(access_token_bearer),
):
    """获取我的会话列表"""
    current_uid = user_details["user"]["user_uid"]
    total, conversations = await message_service.crud_get_user_conversations(
        db, current_uid, page, page_size
    )
    return success_response(
        data={"total": total, "conversations": conversations}, message="获取成功", )


@router.get("/conversations/{conv_id}/messages", response_model=Envelope[MessagePageOut])
async def get_messages(
        conv_id: int,
        db: AsyncSession = Depends(get_database),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50, ge=1, le=100),
        user_details=Depends(access_token_bearer),
):
    """获取会话历史消息（时间正序）"""
    current_uid = user_details["user"]["user_uid"]
    total, messages = await message_service.crud_get_messages(
        db, conv_id, current_uid, page, page_size
    )
    return success_response(
        data={"total": total, "messages": messages, "current_uid": current_uid},
        message="获取成功",
    )


@router.post("/conversations/{conv_id}/messages", response_model=Envelope[MessageOut])
async def send_message(
        conv_id: int,
        message_data: MessageCreateModel,
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """发送消息"""
    current_uid = user_details["user"]["user_uid"]
    msg = await message_service.crud_add_message(
        db, conv_id, current_uid, message_data.content
    )
    return success_response(data=msg, message="发送成功")


@router.get("/users/search", response_model=Envelope[list[UserBriefOut]])
async def search_users(
        keyword: str = Query(..., min_length=1, max_length=50, description="搜索关键词"),
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """搜索用户（昵称/用户名/邮箱模糊匹配），用于添加私信对象

    ## 本次顺手修掉的问题
    原来这里调 _user_brief()，那个函数返回 uid/nickname/username/**email**/level/is_superuser。
    而 crud_search_users 支持按 email 模糊匹配（User.email.like(kw)）——
    于是搜一个 "@qq.com" 就能批量捞到别人的邮箱和管理员身份，
    等于把 8/27 修好的"防邮箱枚举"从后门重新打开。
    现在改成走共享的 UserBriefOut（不含 email），泄露关闭；
    搜索能力本身保留（仍可按邮箱模糊匹配），只是不回显邮箱。
    """
    current_uid = user_details["user"]["user_uid"]
    users = await message_service.crud_search_users(db, keyword, exclude_uid=current_uid)
    return success_response(data=users, message="获取成功")
