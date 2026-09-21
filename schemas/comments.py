from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from schemas.user import UserBriefOut


class CommentsCreateModel(BaseModel):
    content: str
    parent_id: Optional[int] = None  # 楼中楼回复时指定父评论id


# ============ 输出模型（白名单）============

class _CommentBase(BaseModel):
    """评论的公共字段（帖子评论与商品评论共用一套形状）

    ## comment
    ### 这里用继承是合适的
    判据和 UserBriefOut 那条一致：**"同一个东西的不同深度"用继承，
    "不同契约"才要分开建。**
      - CommentReplyOut / CommentOut 是同一个评论、只是层级不同 → 继承
      - UserOutModel / UserBriefOut 是两种不同的暴露契约 → 不继承、分开建
    ### model_config 会被子类继承
    这里的 from_attributes 属于【Python 类继承】，子类自动带上。
    （注意别和另一件事混淆：嵌套字段里的模型【不会】继承父模型的 model_config，
      比如 PostOut.author 是 UserBriefOut，那 UserBriefOut 必须自己写 from_attributes。）
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    post_id: int
    author_uid: str
    parent_id: Optional[int] = None
    created_time: datetime
    author: Optional[UserBriefOut] = None


class CommentReplyOut(_CommentBase):
    """楼中楼子回复

    ## comment
    ### 为什么这里【不】再有 replies
    前端只渲染一层楼中楼（PostDetailView.vue 里 `v-for="reply in comment.replies"`，
    模板里不再用 reply.replies）。而 crud 的预加载深度也只有一层：
        selectinload(Comments.replies).selectinload(Comments.author)
    如果这里也放 replies，Pydantic 会继续往下读 reply.replies——
    那是【未加载】的关系，异步下会抛 MissingGreenlet 直接 500。
    所以深度必须和 crud 的预加载深度对齐：一层就是一层。
    将来要做无限嵌套，得同时改 crud（递归预加载）和这里，
    并给模型设一个深度上限，否则会无限递归。
    """


class CommentOut(_CommentBase):
    """一级评论（带它的楼中楼子回复）

    ## comment
    ### replies 的默认值必须是 []
    crud_add_new_comment_into_post 已经在 refresh 里加载了 replies，所以新增评论也有值。
    默认值 [] 是给"万一没预加载"兜底的 —— 注意它只保护"属性不存在"，
    如果属性存在但读取会报错（未加载的关系），默认值救不了。
    """
    replies: list[CommentReplyOut] = []


class CommentPageOut(BaseModel):
    """帖子评论列表的 data 形状：{total, comments}

    ## comment
    ### 为什么要有这个模型（本次修的 total bug）
    原来 /getcomments 只返回了评论列表本身，total 被丢掉了：
        return success_response(data=comments_list, ...)
    而前端 PostDetailView 读的是 res.total（平级），永远是 undefined → 0，
    表现为"评论 (0)"、分页条也不显示。这是 9/4 就记录下来的问题。

    现在把 total 收进 data，前端改读 res.data.total。
    ### 字段名用 comments 而不是 list
    商品评论接口原来用的是 list —— 但 list 会遮蔽 Python 内建名，
    而且两个几乎一样的"评论列表"接口用不同字段名迟早出事。
    所以本次统一成 comments（商品评论那边也一起改了）。
    ### 为什么不复用 common.py 的 PageOut
    PageOut 的字段是 {total, items}，和这里的 comments 不同名。
    以后若要把全站分页统一成 {total, items}，再一起换。
    """
    total: int
    comments: list[CommentOut]
