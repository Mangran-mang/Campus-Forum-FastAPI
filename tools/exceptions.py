# 全局异常处理模块
from typing import Any, Callable

from fastapi import Request, HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi.responses import JSONResponse
from starlette import status


class UserException(Exception):
    """用户方面出现问题"""
    pass


class PostException(Exception):
    """帖子方面出现问题"""
    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        self.message = message


class CommentsException(Exception):
    """评论方面出现问题"""
    pass

class GoodsException(Exception):
    """商品方面出现问题"""
    pass

class AIException(Exception):
    """AI方面出现问题"""
    pass


# 三种不存在异常
async def post_not_found_error(request: Request, exc: PostException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={
            "异常类型": exc.error_type,
            "异常信息": exc.message,
        }, )


async def user_not_found_error(request: Request, exc: UserException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={
            "异常类型": "用户异常",
            "异常信息": "未查找到对应的用户信息",
        }, )


async def comments_not_found_error(request: Request, exc: CommentsException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={
            "异常类型": "评论异常",
            "异常信息": "未查找到对应的评论",
        }, )


# http异常
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code, content={
            "异常类型": "HTTP异常",
            "异常信息": exc.detail,
        }, )


# 数据库操作异常
async def db_exception_handler(request: Request, exc: IntegrityError):
    error_msg = str(exc.orig)  # orig 属性返回原始错误信息
    if "username_UNIQUE" in error_msg or "Duplicate entry" in error_msg:
        detail = "用户名已存在"
    elif "FOREIGN KEY" in error_msg:
        detail = "用户不存在"
    else:
        detail = "数据库约束冲突"

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={
            "异常类型": "数据库异常",
            "异常定位": detail,
            "异常信息": str(exc),
        }, )


# sqlalchemy异常
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={
            "异常类型": "sqlalchemy异常",
            "异常信息": str(exc)
        }, )


# 其他异常
async def other_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={
            "异常类型": "其他异常",
            "异常信息": str(exc),
        }, )

# 异常创造工厂函数
def create_exception_handler(status_code: int,initial_message: Any) -> Callable[[Request, Exception],JSONResponse]:
    async def exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status_code,
            content={
                "异常类型": "请重写改内容",
                "异常信息": str(exc),
                "初始信息": initial_message
            }, )
    return exception_handler