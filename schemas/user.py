from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict, Field


class UserCreateModel(BaseModel):
    email:EmailStr
    password:str = Field(...,min_length=8)
    username: Optional[str] = None
    nickname: Optional[str] = None
    # avatar_url: Optional[str] = None
    gender: Optional[str] = "未知"
    # is_active: Optional[bool] = True
    # is_superuser: Optional[bool] = False

class UserUpdateModel(BaseModel):
    email: EmailStr
    password: str = Field(default=None, min_length=8)
    # ## 为什么这两个都得是 Optional[str]（2026-09-25）
    # 原写法 `str = None`：注解是 str（不含 None）而默认值是 None，
    # Pydantic v2 实测行为是"两副面孔"——
    #   不传该字段 → 走默认值，而**默认值不参与校验** → 通过（正常路径看不出问题）
    #   显式传 null → 校验 None 是不是 str → **422 `Input should be a valid string`**
    # 而 ProfileView.vue 的 handleSave 传的是 `editForm.xxx || null`，
    # 用户清空用户名/昵称再保存就会撞上第二条。
    # ⚠️ 注意 `gender: str = None` 保持原样是有意为之：前端那个字段来自
    # select（值恒为 男/女/未知），不会传 null；而 user.gender 列是
    # Enum('男','女','未知') NOT NULL，放开成 Optional 反而会让 None
    # 穿过 Pydantic 校验、最后在数据库层炸成 400。要放开得先配 crud 侧的"None 不写回"。
    username: Optional[str] = None
    nickname: Optional[str] = None
    # avatar_url: str = None
    gender: str = None
    # is_active: Optional[bool] = True
    # is_superuser: Optional[bool] = False


class ChangePasswordModel(BaseModel):
    """修改密码的输入模型（2026-09-23 新增）

    ## comment
    ### 为什么单独建模型，而不是复用 UserUpdateModel
    UserUpdateModel 是"改资料"的通用模型，它**不要求提供原密码** ——
    昵称、性别这类字段本来就不敏感。
    但改密码是敏感操作：只凭一个有效 token（token 被盗、或 XSS 拿到 localStorage）
    就能改掉密码，等于账号被永久锁死。所以必须单独开一条路，强制校验原密码。
    判据和 UserOutModel / UserBriefOut 那次一致：**不同契约才拆模型**。

    ### 为什么 old_password 不写 min_length
    老密码可能是历史规则下设的 —— 注册接口在 2026-09-23 之前**没有任何长度约束**，
    存量用户的密码可能是 6 位、1 位甚至空串。
    若给 old_password 也加 min_length=8，这批人**永远改不了密码**：
    输入框里填的是他们的真实旧密码，却因为不符合新规则被 422 挡在门外。
    长度规则是给**新密码**立的 —— 约束入口，不追溯存量。
    旧密码填错了自然会在 verify_password 那一步失败（401）。
    """
    old_password: str
    new_password: str = Field(..., min_length=8)

class UserLoginModel(BaseModel):
    email: EmailStr
    password: str

class UserOutModel(BaseModel):
    ## 对外输出的用户信息白名单，password 永远不进这个模型
    model_config = ConfigDict(from_attributes=True)  # 允许直接从 ORM 对象读取属性

    uid: str
    email: str
    is_superuser: bool  # 再按前端需要补：昵称、头像、experience、level 等
    gender:str
    nickname:str
    level:int
    experience:int
    # ## 为什么补上 created_time（2026-09-23）
    # 前端 ProfileView 的"注册时间"一直显示空白，根因就在这：
    # **response_model 只会输出模型【声明过】的字段**，ORM 对象上明明有 created_time，
    # 但这里没声明，就被静默滤掉了（不报错、不警告），前端拿到的是 undefined，
    # formatTime 里 `if (!t) return ''` 于是返回空串。
    # 这是"白名单模型"的固有代价：字段必须显式登记，漏了表现为"功能静默失效"而不会报错。
    # 注册时间给自己看是合理的（UserOutModel 本就是"自己看自己"的契约），
    # 但**不要**往 UserBriefOut 里加——那是给外人看的，注册时间属于可被用来做用户画像的信息。
    created_time: datetime


# ========== 对外的用户摘要（所有"别人看我"的场景共用）==========

class UserBriefOut(BaseModel):
    """对外的用户摘要：帖子作者、评论作者、商品作者、消息对方、搜索结果……

    ## comment
    ### 为什么不能复用 UserOutModel
    UserOutModel 含 email / experience——它服务的是"自己看自己"，
    用户看自己的邮箱天经地义；但同一份数据给"任何登录用户"看就是泄露。
    所以两者不是重复定义，是两个不同的契约：
      UserOutModel  = 身份证（只给本人）
      UserBriefOut  = 名片（给所有外人）

    ### 为什么抽成一个共享模型而不是每处各写一个
    "哪些字段能对外"这个决定必须只有一个地方做。
    如果 posts 写 PostAuthorOut、comments 写 CommentAuthorOut、
    搜索再写一个，就会在 N 个地方各自决定"要不要给 email"——迟早漏一个。
    （goods 模块的 GoodsAuthorOut 就是这个模型，可以直接换成引用这里。）

    ### 字段判据
    只有一条：泄露给任何登录用户都不心疼。
    - email   ❌ 只给本人
    - password ❌ 哈希也不行，永不进任何输出模型
    - username/昵称/等级/管理员标记 ✅ 前端本来就要显示
    """
    model_config = ConfigDict(from_attributes=True)

    uid: str
    nickname: Optional[str] = None      # ORM 里可空
    username: Optional[str] = None      # ORM 里可空；前端昵称为空时会退回显示它
    level: int
    is_superuser: bool                  # 前端用它显示"管理员"标签，非私人信息


# ========== 登录 / 令牌 相关 ==========

class LoginUserOut(BaseModel):
    """登录响应里夹带的 user 信息

    ## comment
    ### 这里【不能】用 UserOutModel
    登录响应里带上整个 UserOutModel 是多余的（level/experience/gender 这些
    前端登录后调 /current_user 就能拿到）。而且登录是最容易被抓包的接口，
    带的信息越少越好。所以只给"下一步要用"的三样：
      - uid：后续请求要它
      - email：前端显示"你已登录为 xxx"
      - is_superuser：决定前端要不要显示管理入口
    """
    email: str
    uid: str
    is_superuser: bool


class LoginOut(BaseModel):
    """POST /login 的 data 形状：{access_token, refresh_token, user}

    ## comment
    ### 令牌出现在响应模型里，意味着会进 OpenAPI 文档
    这是登录接口的正常做法（文档里描述"返回两个令牌"是应该的），
    但要清楚：OpenAPI 是公开可访问的（/openapi.json 无鉴权），
    所以不要在这里加"示例值"，也别把真实的 token 写进 examples/description。
    ### 为什么两个 token 的名字都带 _token 后缀
    沿用现有响应字段名，前端不用改。
    """
    access_token: str
    refresh_token: str
    user: LoginUserOut


class TokenPairOut(BaseModel):
    """POST /refresh_token 的 data 形状：{access_token, refresh_token}

    ## comment
    刷新接口做的是"轮换"：每次刷新同时给新 access 和新 refresh，
    所以两个字段都是必填，没有"只刷新 access"的情况。
    """
    access_token: str
    refresh_token: str