# 全局异常处理模块
"""
统一异常响应格式
================

本项目所有异常响应（业务异常 / HTTPException / 参数校验异常 / 数据库异常 /
未捕获异常）经本模块处理后，响应体统一为：

    {
        "code": 404,               # int，与 HTTP 状态码保持一致
        "message": "帖子不存在",    # str，可以直接展示给用户的错误描述
        "data": None               # 异常场景固定为 None
    }

约定
----
1. code 与 HTTP 状态码一致：前端用 res.status 还是 body.code 判断都一样，
   不需要维护两套码表。
2. message 只放"能给用户看"的话：SQL 语句、堆栈、原始异常文本一律只进日志，
   不再回传给前端（避免泄露表结构等内部信息）。
3. data 在异常场景恒为 None —— 唯一的例外是 422 参数校验失败，
   此时 data 携带字段级错误明细，方便前端表单回显。
4. 使用方式：业务代码里 raise 一个异常即可，不要自己拼 JSONResponse：
       raise PostException("帖子不存在")                  # 用子类的默认状态码
       raise APIException("余额不足", status_code=400)    # 临时指定状态码
"""
from typing import Any, Callable, Optional
import logging
from http import HTTPStatus

logger = logging.getLogger(__name__)

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi.responses import JSONResponse
from starlette import status


# 常用状态码的默认文案：当异常本身没带消息时兜底，避免把空串或原始异常抛给前端
HTTP_STATUS_MESSAGE = {
    400: "请求参数错误",
    401: "未登录或登录已失效",
    403: "没有权限执行该操作",
    404: "请求的资源不存在",
    405: "请求方法不被允许",
    409: "资源冲突",
    413: "上传内容过大",
    422: "请求参数校验失败",
    429: "请求过于频繁，请稍后再试",
    500: "服务器内部错误",
    502: "上游服务调用失败",
    503: "服务暂时不可用",
}


def success_response(data: Any = None, message: str = "ok", code: int = status.HTTP_200_OK) -> dict:
    """构造统一格式的成功响应体
    ## comment
    和 error_response 成对，保证前后端只认一种结构：
        {"code": 200, "message": "ok", "data": <业务数据>}
    路由里直接 return 这个函数的返回值即可，不要自己拼字典，
    否则又会出现"有的有 data 有的没有、有的多个 total"这种不一致。
    data 缺省为 None（如纯删除操作没有内容可返回）；
    code 留给新增资源返回 201 这类场景，默认 200。
    """
    return {"code": code, "message": message, "data": data}


def _status_phrase(code: int) -> Optional[str]:
    """返回状态码对应的标准英文短语（404 -> "Not Found"）
    ## comment
    用来判断 detail 是不是框架补的默认值：Starlette/FastAPI 抛 HTTPException
    时如果没给 detail，就会自动填这个短语。是默认值就没必要展示给用户，
    换成 HTTP_STATUS_MESSAGE 里的中文文案。
    """
    try:
        return HTTPStatus(code).phrase
    except ValueError:
        return None


def error_response(code: int, message: Any = None, data: Any = None) -> dict:
    """构造统一格式的错误响应体
    ## comment
    所有异常处理器都必须通过它生成 content，保证返回结构一致。
    message 为 None / 空时按状态码兜底；非字符串时转成字符串，
    防止把 dict、异常对象之类的原始结构直接塞进响应。
    """
    if not message:
        message = HTTP_STATUS_MESSAGE.get(code, "请求失败")
    elif not isinstance(message, str):
        message = str(message)
    return {"code": code, "message": message, "data": data}


class APIException(Exception):
    """业务异常基类

    子类只需要声明 status_code 和 default_message，
    异常处理器会自动把它转成统一格式的响应。

    用法:
        raise APIException("余额不足", status_code=400)
        raise PostException("帖子不存在")
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    default_message: str = "请求失败"

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        status_code: Optional[int] = None,
        data: Any = None,
    ):
        self.message = message or self.default_message
        if status_code is not None:
            self.status_code = status_code
        self.data = data
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.status_code}] {self.message}"


class UserException(APIException):
    """用户方面出现问题"""
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "未查找到对应的用户信息"


class PostException(APIException):
    """帖子方面出现问题"""
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "不存在当前查找的帖子"

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        error_type: Optional[str] = None,
        status_code: Optional[int] = None,
        data: Any = None,
    ):
        # error_type 只用于日志分类，不再出现在响应体里
        self.error_type = error_type or "帖子异常"
        super().__init__(message, status_code=status_code, data=data)


class CommentsException(APIException):
    """评论方面出现问题"""
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "未查找到对应的评论"


class GoodsException(APIException):
    """商品方面出现问题"""
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "商品不存在"


class AIException(APIException):
    """AI 方面出现问题

    AI 属于上游依赖，它挂了不是本服务的 500，用 502 语义更准确。
    """
    status_code = status.HTTP_502_BAD_GATEWAY
    default_message = "AI 服务调用失败"


# ---------- 异常处理器 ----------

async def api_exception_handler(request: Request, exc: APIException):
    """业务异常统一处理

    ## comment
    注册一次 APIException 即可覆盖所有子类：Starlette 查找 handler 时
    会沿 type(exc).__mro__ 逐级向上找，所以 UserException / PostException
    这类子类都会落到这里，不用逐个注册。
    4xx 是正常业务流程（用户输错、资源不存在），只 warning；
    5xx 才是真的出事了，用 exception 记完整堆栈。
    """
    error_type = getattr(exc, "error_type", None)
    prefix = f"[{error_type}] " if error_type else ""

    if exc.status_code >= 500:
        logger.exception("%s业务异常 %s: %s", prefix, exc.status_code, exc.message)
    else:
        logger.warning("%s业务异常 %s: %s", prefix, exc.status_code, exc.message)

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.status_code, exc.message, exc.data),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTPException 处理

    ## comment
    项目里绝大多数错误都是直接 raise HTTPException(status_code=..., detail=...)，
    这里把 detail 映射成 message。两种特殊情况：
    1. detail 不是字符串（少数情况下会传 dict/list）→ 放回 data，
       message 用状态码兜底文案，保证 message 一定是字符串；
    2. detail 是英文状态短语（"Not Found" / "Method Not Allowed"）→
       这是框架自己抛的（路由没匹配上、方法不允许），没有业务信息，
       换成 HTTP_STATUS_MESSAGE 里的中文文案，别把英文原文丢给用户。

    参数类型刻意用 starlette 的 HTTPException（fastapi 的那个是它的子类）：
    路由没匹配上时 Starlette 抛的是父类，只注册 fastapi 的子类会漏掉这些错误。
    """
    if exc.status_code >= 500:
        logger.exception(exc)
    else:
        logger.warning("HTTP %s: %s", exc.status_code, exc.detail)

    code = exc.status_code
    detail = exc.detail

    if not isinstance(detail, str):
        content = error_response(code, None, detail)
    elif detail == _status_phrase(code):
        content = error_response(code)
    else:
        content = error_response(code, detail)

    return JSONResponse(status_code=code, content=content)


async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数校验失败（422）

    ## comment
    默认 422 返回的是 FastAPI 原始的 errors 数组，结构和其它错误不一致。
    这里改成统一格式，并把字段级明细放进 data（唯一 data 不为 None 的场景），
    方便前端做表单错误回显。loc 里的第一个元素是 "body"/"query" 这种位置信息，
    去掉只保留真正的字段名。
    """
    errors = [
        {
            "field": ".".join(str(part) for part in e.get("loc", ())[1:]) or "body",
            "message": e.get("msg", ""),
        }
        for e in exc.errors()
    ]
    logger.warning("参数校验失败 %s %s: %s", request.method, request.url.path, errors)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "请求参数校验失败",
            errors,
        ),
    )


async def db_exception_handler(request: Request, exc: IntegrityError):
    """数据库完整性约束冲突

    ## comment
    从 exc.orig 拿数据库原始报错做分类，只把结论性的中文文案返回给前端，
    原始 SQL 错误信息只进日志 —— 线上把表结构/字段名抛出去是安全隐患。
    """
    logger.exception(exc)
    error_msg = str(exc.orig)  # orig 属性返回原始错误信息
    if "username_UNIQUE" in error_msg or "Duplicate entry" in error_msg:
        message = "用户名已存在"
    elif "FOREIGN KEY" in error_msg:
        message = "用户不存在"
    else:
        message = "数据冲突，请检查提交的内容"

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response(status.HTTP_400_BAD_REQUEST, message),
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """其它数据库异常"""
    logger.exception(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "数据库操作失败，请稍后重试",
        ),
    )


async def other_exception_handler(request: Request, exc: Exception):
    """兜底：未捕获的异常

    ## comment
    只返回通用文案 + 500，具体错误靠日志排查，不把内部细节暴露给调用方。
    """
    logger.exception(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "服务器内部错误",
        ),
    )


def create_exception_handler(
    status_code: int, initial_message: Any
) -> Callable[[Request, Exception], JSONResponse]:
    """异常处理器工厂：给某个异常类型配一个固定文案的固定状态码

    ## comment
    用于"某个异常类型永远只对应一种响应"的场景，比单独写一个 handler 省事。
    注意：如果抛的是 APIException 子类，直接用类上的 status_code /
    default_message 即可，不需要走这个工厂。
    """
    async def exception_handler(request: Request, exc: Exception):
        logger.warning(
            "异常 %s: %s", type(exc).__name__, initial_message
        )
        return JSONResponse(
            status_code=status_code,
            content=error_response(status_code, initial_message),
        )
    return exception_handler
