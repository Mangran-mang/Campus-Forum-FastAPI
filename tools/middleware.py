import logging

from alembic.util import status
from fastapi import FastAPI,status
from fastapi.requests import Request
import time
from starlette.middleware.cors import CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config.config import Config

def register_middleware(app: FastAPI):
    """
    注册中间件
    """
    @app.middleware("http")
    async def custom_loggin(request: Request, call_next):
        # 进来时先执行call_next以上的代码
        # ---------- 关键步骤：把请求传给下一个环节 ----------
        # call_next 是 FastAPI 提供的函数，调用它会把请求传给：
        # 下一个中间件 → 最后到你的接口路由
        # 执行完会拿到接口返回的 response
        response = await call_next(request)
        message = f"{request.client.host} {request.method} {request.url.path} {response.status_code}"
        logging.getLogger("app.http").info(message)
        return  response

    app.add_middleware(  # 设置app可被跨域访问
        CORSMiddleware,  # 中间件类 跨域中间件
        allow_origins=[o.strip() for o in  Config.CORS_ORIGINS.split(",")],  # *代表所有，允许所有源访问，这里需要换成自己的域名
        allow_credentials=True,  # 允许携带cookie
        allow_methods=["*"],  # 允许所有请求方法
        allow_headers=["*"],  # 允许所有请求头
    )

    # @app.middleware("http")
    # async def authorization(request:Request,call_next):
    #     if not "Authorization" in request.headers:
    #         return JSONResponse(
    #             content={
    #                 "信息":"未通过认证",
    #                 "提示":"请提供正确的令牌"
    #             },
    #             status_code = status.HTTP_401_UNAUTHORIZED
    #         )
    #     response = await call_next(request)
    #     return response

