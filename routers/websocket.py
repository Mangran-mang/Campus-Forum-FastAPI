from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocket, WebSocketDisconnect

from config.database_config import get_database
from crud.message import MessageService
from tools.connection import ConnectionManager
from tools.security import decode_token

router = APIRouter(prefix="/ws",tags=["用户私信"])

connect_manager = ConnectionManager()
message = MessageService()


@router.websocket('/chat/{conv_id}')
async def chat(websocket: WebSocket, conv_id: int,db:AsyncSession=Depends(get_database)):
    # 从URL中取token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)  # 1008 = 策略违规，拒绝连接
        return

    token_data = decode_token(token)
    if not token_data:
        await websocket.close(code=1008)
        return

    current_uid = token_data['user']['user_uid']

    # 开始查会话拿目标用户uid
    conv = await message.crud_get_conversation(db, conv_id, current_uid)
    other_uid = conv.user_b_uid if conv.user_a_uid == current_uid else conv.user_a_uid

    # 登记连接
    await connect_manager.connect(current_uid, websocket)

    # 循环收发
    try:
        while True:
            text = await websocket.receive_text()      # 收
            await message.crud_add_message(db, conv_id, current_uid, text)         # 落库
            # 信号同时推给双方：对方立即刷新，自己也能看到刚发的消息
            await connect_manager.send_to_user(other_uid, text)
            await connect_manager.send_to_user(current_uid, text)
    except WebSocketDisconnect:
        connect_manager.disconnect(current_uid, websocket)  # disconnect 是同步函数，不加 await
