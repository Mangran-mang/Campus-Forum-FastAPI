from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from schemas.category import CategoryOut
from schemas.user import UserBriefOut


# ============ 输入模型============
class PostsCreateModel(BaseModel):
    """
    需要标题、内容
    author_uid 由 token 自动填充，前端无需传入

    ## 为什么没有 is_top（2026-09-21 删）
    "置顶"是【管理动作】，不是发帖人能自选的属性。
    留着它的后果实测过：任何注册用户 POST {"is_top": true} 就能把自己的帖子
    插到【全站列表最前面】——因为 crud_get_posts_list 的 ORDER BY
    （is_top desc, created_time desc）对不带 author_uid 的列表同样生效，
    前端只是按返回顺序渲染，所以"前端没实现置顶"根本挡不住。
    删掉字段 = 默认安全；置顶改由管理员接口 /api/posts/admin/set_top 做。
    """
    title: str
    content: str
    summary: Optional[str] = None
    is_public: bool = True
    category_id: Optional[int] = None
    author_uid: Optional[str] = None  # 由后端从 token 获取


class PostsUpdateModel(BaseModel):
    """
    需要标题、内容

    ## 为什么没有 is_top
    同 PostsCreateModel：置顶走管理员专用接口，不在"改帖子内容"这条路里。
    """
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    is_public: Optional[bool] = None
    category_id: Optional[int] = None


class PostTopModel(BaseModel):
    """置顶请求体（仅管理员接口使用）

    ## comment
    ### 为什么单独建一个模型，而不是复用 PostsUpdateModel
    职责不同：PostsUpdateModel 描述"改帖子内容"，置顶是"改管理属性"。
    混在一起的话，以后给 PostsUpdateModel 加字段时会不自觉地把管理属性也带进去
    ——今天这个漏洞就是这么来的。
    ### 为什么用一个 bool 而不是两个接口（置顶/取消置顶）
    一个幂等接口（is_top=true/false）比两个接口少一半路由，前端也好写。
    """
    is_top: bool


# ============ 输出模型（白名单）============

class PostOut(BaseModel):
    """帖子输出：列表、详情、创建、更新都复用它

    ## comment
    ### 为什么 author 用共享的 UserBriefOut，而不是在这里再写一个 PostAuthorOut
    你之前写的 PostAuthorOut 其实就是 UserBriefOut（uid/nickname/level），
    而且是【未定义】状态（会 NameError）。
    真正的问题不是"哪个名字对"，而是"要不要在这里再定义一遍"——不要，因为：
      "哪些字段能给外人看"这个决定必须只有一个地方做。
      在这里再写一份，以后给 User 加字段（或发现有字段不该露）时，
      就得记得同步 posts / comments / goods / message / 搜索…… 迟早漏一个。

    ### 为什么 category 也不单独写 PostCategoryOut，直接用共享的 CategoryOut
    判据是：**不同场景该暴露的字段是否真的不同**。
      - User 有这种情况（email 只给本人）→ 所以要拆 UserOutModel / UserBriefOut
      - Category 没有这种情况（板块信息对谁都是一样的：名字、图标、排序）
        → 拆开只是重复，没有收益。前端选板块的下拉框本来就要 name/icon/sort_order。

    ### author / category 为什么是 Optional
    两者都是可空外键（category_id 可空；author 理论必有但关系可能没预加载）。
    ⚠️ 但注意：Optional 只保护"属性不存在 / 值为 None"这两种情况。
    如果 crud 里忘了 selectinload(Posts.author)，读它会在异步下抛 MissingGreenlet
    ——那不是 500 里的 null，而是当场报错。
    所以挂 response_model 的接口，crud 必须把模型用到的关系全部预先加载。

    ### 两个时间都给
    created_time 来自 Base（发布时刻），updated_time 带 onupdate（每次编辑会变）。
    前端显示"发布于"用 created_time。
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    summary: Optional[str] = None
    view_count: int
    is_public: bool
    is_top: bool
    category_id: Optional[int] = None
    author_uid: str
    created_time: datetime
    updated_time: datetime
    author: Optional[UserBriefOut] = None
    category: Optional[CategoryOut] = None


class ReviewResultOut(BaseModel):
    """AI 审核结果（/report 接口的 data）

    ## comment
    ### 为什么不复用 PostOut
    report_post 的 data 是 AI 的判定结果，不是一个帖子——而且判定违规时帖子已经被删了，
    更没有 PostOut 可给。之前误把 Envelope[PostOut] 挂到这个接口上，
    data 里只有 violated/type/reason 三个键，缺 PostOut 的全部必填字段，
    会直接抛 9 个 validation error（实测）。
    ### 三个字段都给默认值
    AI 返回可能缺键（调用处用的是 review_result.get(...)），
    给默认值可以避免"AI 少返一个字段就 500"。
    ### type 字段名
    沿用 AI 返回的原始键名 type（不改成 violation_type），
    避免调用处还要做一次键名映射。
    """
    violated: bool = False
    type: str = ""
    reason: str = ""
