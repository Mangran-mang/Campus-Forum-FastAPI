from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BookmarkActionModel(BaseModel):
    post_id: int


# ============ 输出模型（白名单）============

class BookmarkOut(BaseModel):
    """单条收藏记录

    ## comment
    ### 为什么没有嵌套 post
    前端目前只用它判断"当前帖子有没有被收藏"：
        isBookmarked = res.data.some(b => b.post_id === postId)
    所以只给 post_id 就够，不需要把帖子整条带出来（省一次查询、少一份数据）。
    将来若要做"我的收藏"列表页、要显示帖子标题作者，
    再在这里加 post: Optional[PostOut] 并在 crud 里 join，
    不要在现在就把它加上——用不到的关系带着只会变成懒加载的坑。

    ### 顺带一个优化点（非必须）
    现在 /bookmarks/my 会把该用户的全部收藏行拉回来，只为判断一个帖子。
    收藏多了以后可以加 GET /bookmarks/status?post_id= 只查一条，
    或直接在帖子详情响应里带一个 is_bookmarked 字段。
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    user_uid: str
    created_time: datetime


class BookmarkToggleOut(BaseModel):
    """收藏/取消收藏的 data 形状：{bookmarked}"""
    bookmarked: bool
