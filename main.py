from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from routers import user,posts,comments,agent,category,like,bookmark,notification
from config import database_config
from models import model_base
import models
from tools.middleware import register_middleware
from tools.exceptions import (
    UserException,
    PostException,
    CommentsException,
    http_exception_handler,
    db_exception_handler,
    sqlalchemy_exception_handler,
    other_exception_handler,
    post_not_found_error,
    user_not_found_error,
    comments_not_found_error
)


def register_exception_handler(fapp):
    fapp.add_exception_handler(HTTPException, http_exception_handler)
    fapp.add_exception_handler(IntegrityError, db_exception_handler)
    fapp.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    fapp.add_exception_handler(Exception, other_exception_handler)
    fapp.add_exception_handler(PostException, post_not_found_error)
    fapp.add_exception_handler(UserException, user_not_found_error)
    fapp.add_exception_handler(CommentsException, comments_not_found_error)



@asynccontextmanager
async def lifespan(app: FastAPI):
    print("如果需要改ORM模型，则到main函数中重新启用init_db函数")
    # await init_db()
    yield
app = FastAPI(lifespan=lifespan)
# app.lifespan = lifespan
register_exception_handler(app)
register_middleware(app)



app.include_router(user.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(agent.router)
app.include_router(category.router)
app.include_router(like.router)
app.include_router(bookmark.router)
app.include_router(notification.router)