from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException,status
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.responses import JSONResponse

from routers import user,posts,comments,category,like,bookmark,notification,goods,goods_classify,goods_comment,image,message
from config import database_config
from models import model_base
import models
from tools.middleware import register_middleware
from tools.exceptions import (
    UserException, PostException, CommentsException, GoodsException,
    http_exception_handler, db_exception_handler, sqlalchemy_exception_handler,
    other_exception_handler, post_not_found_error, user_not_found_error,
    comments_not_found_error, create_exception_handler, AIException,
)


def register_exception_handler(fapp):
    fapp.add_exception_handler(HTTPException, http_exception_handler)
    fapp.add_exception_handler(IntegrityError, db_exception_handler)
    fapp.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    fapp.add_exception_handler(Exception, other_exception_handler)
    fapp.add_exception_handler(PostException, post_not_found_error)
    fapp.add_exception_handler(UserException, user_not_found_error)
    fapp.add_exception_handler(CommentsException, comments_not_found_error)
    fapp.add_exception_handler(
        GoodsException,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_message="商品不存在"
        )
    )
    @app.exception_handler(500)
    async def internal_server_error(request, exc):
        return JSONResponse(
            status_code=500,
            content={
                "异常类型": "服务器内部错误",
                "异常信息": str(exc),
            },
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("项目已完全启动")
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

# 挂载静态文件目录用作图床
import os
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")