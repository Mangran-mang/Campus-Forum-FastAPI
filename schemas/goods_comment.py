from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from schemas.user import UserBriefOut


class GoodsCommentCreateModel(BaseModel):
    content: str
    parent_id: Optional[int] = None  # 楼中楼回复时指定父评论id


# ============ 输出模型（白名单）============

class _GoodsCommentBase(BaseModel):
    """商品评论的公共字段

    ## comment
    结构与帖子评论（schemas/comments.py 的 _CommentBase）对齐——
    同一个"评论"概念、两张表，区别只在归属字段：帖子用 post_id，商品用 goods_gid。
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    goods_gid: str
    author_uid: str
    parent_id: Optional[int] = None
    created_time: datetime
    author: Optional[UserBriefOut] = None


class GoodsCommentReplyOut(_GoodsCommentBase):
    """商品评论的楼中楼子回复

    ## comment
    ### 为什么这里不再有 replies
    同帖子评论：前端只渲染一层（GoodsDetailView.vue 的
    `v-for="reply in comment.replies"` 里不再用 reply.replies），
    crud 的预加载深度也只有一层（selectinload(GoodsComment.replies)）。
    多写一层就会读到未加载的关系 → 异步下 MissingGreenlet → 500。
    """


class GoodsCommentOut(_GoodsCommentBase):
    """一级商品评论（带它的楼中楼子回复）"""
    replies: list[GoodsCommentReplyOut] = []


class GoodsCommentPageOut(BaseModel):
    """商品评论列表的 data 形状：{total, comments}

    ## comment
    ### 字段名从 list 改成了 comments
    原来叫 list —— list 是 Python 内建名，字段叫这个名字虽然能跑
    （注解 `list[...]` 在字段赋值前求值，取的还是内建），但读起来别扭、容易踩坑。
    更关键的是：帖子评论接口也返回同一个概念，两边字段名不一致迟早出事。
    所以两个接口统一成 {total, comments}。
    """
    total: int
    comments: list[GoodsCommentOut]
