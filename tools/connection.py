import asyncio
import logging
import json


from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from config.redis_config import redis_client
from crud.user import UserService
from tools.exceptions import UserException
WS_CHANNEL = "ws:broadcast" # WebSocket广播频道

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.connect_dict = dict()

    async def connect(self,uid:str,websocket:WebSocket):
        await websocket.accept()
        # 如果对应uid的用户不在字典中,则创建
        # uid作为键,值为websocket列表
        if uid not in self.connect_dict:
            self.connect_dict[uid] = []
        # 如果这个uid在字典中,则把当前的WebSocket对象添加进该uid键对应的列表中
        self.connect_dict[uid].append(websocket)


    def disconnect(self,uid:str,websocket:WebSocket):
        if uid in self.connect_dict:
            self.connect_dict[uid].remove(websocket)

            if not self.connect_dict[uid]:
                del self.connect_dict[uid]

    """async def send_to_user(self, uid: str, text: str):原写法
        connections = self.connect_dict.get(uid)
        if not connections:
            return

        for ws in connections:
            await ws.send_text(text)"""
    async def send_to_user(self, uid: str, text: str):
        connections = self.connect_dict.get(uid)
        if not connections:
            return

        for ws in connections:
            if ws.client_state != WebSocketState.CONNECTED:
                continue                    # 已知断开的，直接跳过
            try:
                await ws.send_text(text)
            except Exception:
                pass                        # 发送这一刻才断的，吞掉，不影响其余连接
    async def broadcast_to_user(self,uid:str,text:str):
        """广播text给所有redis客户端,然后uid对应的客户端收"""
        try:
            await self.publish_ws_event(uid,{"text":text})
        except Exception:
            logger.warning("WS 广播失败，降级为本地推送", exc_info=True)
            await self.send_to_user(uid, text)

    async def publish_ws_event(self,to_uid: str, payload: dict) -> None:
        """发布WebSocket事件，将payload以JSON格式发送给to_uid"""
        await redis_client.publish(
            WS_CHANNEL, json.dumps({"to": to_uid, "data": payload})
        )

        # 初遇问题1：publish是干什么的，为什么要用dumps,如果用dump会怎么样，不都是把python对象给变成json吗
        # 答:把payload广播给在"第一个参数"中的客户端，并不存储
        # 最后会返回一个数，这个数就是收到信息的订阅者数量，可以拿来做检测，这里我选择不写

    async def ws_subscriber_loop(self):
        while True:
            pubsub = redis_client.pubsub()  # 创建一个pubsub对象
            try:
                await pubsub.subscribe(WS_CHANNEL)  # 订阅目标参数这个频道
                while True:
                    msg = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if msg is None:
                        continue
                    data = json.loads(msg["data"])
                    await connect_manager.send_to_user(
                        data["to"], data["data"]["text"]
                    )
            except asyncio.CancelledError:
                raise  # 取消上传，不能吞掉
            except Exception:
                logger.exception("WS 订阅断开，3秒后重连")
                await asyncio.sleep(3)
            finally:
                await pubsub.unsubscribe(WS_CHANNEL) # 取消订阅
                await pubsub.close()

connect_manager = ConnectionManager()# 为什么要在这里实例化，在别处会发生什么，具体说出情况