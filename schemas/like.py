from pydantic import BaseModel


class LikeActionModel(BaseModel):
    post_id: int


# ============ 输出模型 ============

class LikeStatusOut(BaseModel):
    """{liked} —— POST /toggle 和 GET /check 两个接口共用同一个形状

    ## comment
    两个接口都返回"当前是否已点赞"，形状一样，所以共用一个模型；
    将来其中一边要多带字段（比如带总赞数），再拆开。
    """
    liked: bool


class LikeCountOut(BaseModel):
    """{count} —— GET /count/{post_id} 的 data"""
    count: int
