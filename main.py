import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from routers import (
    user, posts, comments, category, like, bookmark, notification, goods,
    goods_classify, goods_comment, image, message, websocket
)
from config import database_config
from models import model_base
import models
from tools.middleware import register_middleware
from tools.exceptions import (
    APIException,
    api_exception_handler, http_exception_handler,
    request_validation_exception_handler, db_exception_handler,
    sqlalchemy_exception_handler, other_exception_handler,
)
from tools.log_config import setup_logging

def register_exception_handler(fapp):
    """
    注册全局异常处理器

    ## comment
    所有异常最终都返回统一结构 {"code": 状态码, "message": 描述, "data": None}。
    注册 APIException 一个就够覆盖它的全部子类（UserException / PostException /
    CommentsException / GoodsException / AIException）——Starlette 查找 handler
    时会沿 type(exc).__mro__ 逐级上溯，子类会自动命中父类的处理器。
    """
    fapp.add_exception_handler(APIException, api_exception_handler)
    fapp.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    # 注册 starlette 的 HTTPException（fastapi 的那个是它的子类，会沿 MRO 上溯命中），
    # 这样路由没匹配上、405 等框架自己抛的错误也会被统一格式
    fapp.add_exception_handler(StarletteHTTPException, http_exception_handler)
    fapp.add_exception_handler(IntegrityError, db_exception_handler)
    fapp.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    fapp.add_exception_handler(Exception, other_exception_handler)

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # print("项目已完全启动")
    logger.info("项目已完全启动")
    # await init_db()
    yield


app = FastAPI(lifespan=lifespan)
# app.lifespan = lifespan
register_exception_handler(app)
register_middleware(app)

app.include_router(user.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(category.router)
app.include_router(like.router)
app.include_router(bookmark.router)
app.include_router(notification.router)
app.include_router(goods.router)
app.include_router(goods_classify.router)
app.include_router(goods_comment.router)
app.include_router(image.router)
app.include_router(message.router)
app.include_router(websocket.router)

# 挂载静态文件目录用作图床
import os

uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

