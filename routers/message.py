from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from crud.message import MessageService
from schemas.message import MessageCreateModel
from tools.dependencies import AccessTokenBearer
from tools.exceptions import success_response

router = APIRouter(prefix="/api/messages", tags=["私信管理"])

message_service = MessageService()
access_token_bearer = AccessTokenBearer()


def _user_brief(user) -> dict | None:
    """用户对象 → 前端展示用摘要"""
    if not user:
        return None
    return {
        "uid": str(user.uid),
        "nickname": user.nickname,
        "username": user.username,
        "email": user.email,
        "level": user.level,
        "is_superuser": user.is_superuser,
    }


def _message_brief(msg) -> dict:
    return {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender_uid": msg.sender_uid,
        "content": msg.content,
        "created_time": msg.created_time.isoformat() if msg.created_time else None,
        "sender": _user_brief(getattr(msg, "_sender", None)),
    }


def _conversation_brief(conv) -> dict:
    return {
        "id": conv.id,
        "user_a_uid": conv.user_a_uid,
        "user_b_uid": conv.user_b_uid,
        "created_time": conv.created_time.isoformat() if conv.created_time else None,
        "updated_time": conv.updated_time.isoformat() if conv.updated_time else None,
        "other_user": _user_brief(getattr(conv, "_other_user", None)),
        "last_message": _message_brief(getattr(conv, "_last_message", None))
        if getattr(conv, "_last_message", None) else None,
    }


@router.post("/conversation")
async def get_or_create_conversation(
        other_uid: str = Query(..., min_length=1, max_length=36, description="对方用户uid"),
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """获取或创建与某用户的会话（幂等：已存在则直接返回）"""
    current_uid = user_details["user"]["user_uid"]
    conv = await message_service.crud_get_or_create_conversation(db, current_uid, other_uid)
    return success_response(data=_conversation_brief(conv), message="获取成功")


@router.get("/conversations")
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
    data = [_conversation_brief(c) for c in conversations]
    return success_response(
        data={"total": total, "conversations": data}, message="获取成功", )


@router.get("/conversations/{conv_id}/messages")
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
    data = [_message_brief(m) for m in messages]
    return success_response(
        data={"total": total, "messages": data, "current_uid": current_uid},
        message="获取成功",
    )


@router.post("/conversations/{conv_id}/messages")
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
    return success_response(data=_message_brief(msg), message="发送成功")


@router.get("/users/search")
async def search_users(
        keyword: str = Query(..., min_length=1, max_length=50, description="搜索关键词"),
        db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """搜索用户（昵称/用户名/邮箱模糊匹配），用于添加私信对象"""
    current_uid = user_details["user"]["user_uid"]
    users = await message_service.crud_search_users(db, keyword, exclude_uid=current_uid)
    data = [_user_brief(u) for u in users]
    return success_response(data=data, message="获取成功")
