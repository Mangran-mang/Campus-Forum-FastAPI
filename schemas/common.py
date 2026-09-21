from typing import TypeVar, Generic

from pydantic import BaseModel

T = TypeVar("T")

class Envelope(BaseModel, Generic[T]):
    """统一响应信封：与 tools/exceptions.py 的 success_response 结构一一对应

    ## comment
    和 success_response / error_response 是同一件事的两个面：
      - success_response 在运行时【造】出这个结构
      - Envelope 在类型层面【描述】这个结构，供 response_model 校验与生成文档
    只写一个 T，就能适配所有接口：
      Envelope[PostOut]            单个
      Envelope[list[PostOut]]      列表
      Envelope[None]               无数据（删除类）
    """
    code: int
    message: str = "ok"
    data: T | None = None


class PageOut(BaseModel, Generic[T]):
    """分页外壳：给需要 total 的接口用（如 /get_posts）"""
    total: int
    items: list[T]