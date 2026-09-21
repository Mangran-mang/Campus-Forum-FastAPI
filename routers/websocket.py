from fastapi import APIRouter, Depends, HTTPException
from starlette.websockets import WebSocket, WebSocketDisconnect

from config.database_config import AsyncSessionLocal
from config.redis_config import is_jti_in_blocklist
from crud.message import MessageService
from tools.connection import ConnectionManager
from tools.security import decode_token

router = APIRouter(prefix="/ws",tags=["用户私信"])

connect_manager = ConnectionManager()
message = MessageService()

async def authenticate_ws_token(token: str) -> dict | None:
    token_data = decode_token(token)
    if not token_data:
        return None                                    # 验签/过期失败
    if token_data.get("refresh"):
        return None                                    # 拒绝 refresh token 冒充
    if await is_jti_in_blocklist(token_data["jti"]):
        return None                                    # 已登出
    return token_data

@router.websocket('/chat/{conv_id}')
async def chat(websocket: WebSocket, conv_id: int):
    # 从URL中取token
    token = websocket.query_params.get("token")
    token_data = await authenticate_ws_token(token)
    if not token_data:# 遗留问题6已修,就是authenticate_ws_token函数
        await websocket.close(code=1008)  # 1008 = 策略违规，拒绝连接
        return
    # token_data = decode_token(token)
    # if not token_data:
    #     await websocket.close(code=1008)
    #     return

    current_uid = token_data['user']['user_uid']

    """# 开始查会话拿目标用户uid,需要注意的是这里有问题,原有的在路由里注入会话工厂会抢连接
    所以改为短会话模式,遗留问题7
    conv = await message.crud_get_conversation(db, conv_id, current_uid)
    other_uid = conv.user_b_uid if conv.user_a_uid == current_uid else conv.user_a_uid"""
    async with AsyncSessionLocal() as db:
        conv = await message.crud_get_conversation(db, conv_id, current_uid)
        other_uid = conv.user_b_uid if conv.user_a_uid == current_uid else conv.user_a_uid

    # 登记连接
    await connect_manager.connect(current_uid, websocket)

    # 循环收发
    try:
        while True:
            text = await websocket.receive_text()      # 收
            async with AsyncSessionLocal() as db:
                await message.crud_add_message(db, conv_id, current_uid, text)         # 落库
            # 信号同时推给双方：对方立即刷新，自己也能看到刚发的消息
            await connect_manager.send_to_user(other_uid, text)
            await connect_manager.send_to_user(current_uid, text)
    except WebSocketDisconnect:
        pass
        # 下面原本是AI写的,只在捕获到异常时调用disconnect,后果相当严重
        # connect_manager.disconnect(current_uid, websocket)  # disconnect 是同步函数，不加 await
    finally:
        connect_manager.disconnect(current_uid, websocket)  # 无论怎么退出都注销登记
