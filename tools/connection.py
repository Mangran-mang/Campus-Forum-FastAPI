from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocket, WebSocketDisconnect
from crud.user import UserService
from tools.exceptions import UserException


class ConnectionManager:
    def __init__(self):
        self.connect_dict = dict()

    async def connect(self,uid:str,websocket:WebSocket):
        await websocket.accept()
        if uid not in self.connect_dict:
            self.connect_dict[uid] = []
        self.connect_dict[uid].append(websocket)


    def disconnect(self,uid:str,websocket:WebSocket):
        if uid in self.connect_dict:
            self.connect_dict[uid].remove(websocket)

            if not self.connect_dict[uid]:
                del self.connect_dict[uid]

    async def send_to_user(self, uid: str, text: str):
        connections = self.connect_dict.get(uid)
        if not connections:
            return

        for ws in connections:
            await ws.send_text(text)