from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from config.redis_config import add_jti_to_blocklist
from crud.admin import AdminService
from crud.user import UserService
from schemas.admin import (
    AdminUserOut,
    AdminPostOut,
    AdminUserPageOut,
    AdminPostsPageOut,
    AdminGoodsPageOut,
    AdminLoginOut,
    AdminOverviewOut,
    AdminTrendsOut,
    AdminDistributionOut,
    DistItemOut,
)
from schemas.common import Envelope
from schemas.goods import GoodsOutModel
from schemas.user import (
    UserLoginModel,
    LoginUserOut,
    UserOutModel,
    UserUpdateModel,
)
from tools import security
from tools.dependencies import UserChecker, AccessTokenBearer
from tools.exceptions import success_response, UserException

access_token_bearer = AccessTokenBearer()

router = APIRouter(prefix="/api/admin", tags=["后台管理"])

user_service = UserService()
# ## 后续所有管理接口（用户管理/统计聚合…）统一挂它
# 见《后台管理开发注意事项》3.5：权限边界要能"扫一眼"看出来 ——
# 漏挂不会报错、不会 500，只会"页面上多了点不该看的数据"。
user_checker = UserChecker(True)
admin_service = AdminService()

# ## 与 routers/user.py 的 DUMMY_HASH 同一个目的：
# 用户不存在时也执行一次同等耗时的哈希计算，把「邮箱不存在」和
# 「密码错误」的响应时间对齐，防止用响应时间差枚举有效邮箱。
# （各 router 模块级自己算一份：保持文件自包含，避免 router 之间互相 import）
DUMMY_HASH = security.get_password_hash("对齐时间的假密码")


@router.post("/login", response_model=Envelope[AdminLoginOut])
async def admin_login(
    login_data: UserLoginModel,
    db: AsyncSession = Depends(get_database),
):
    """
    后台管理员登录：独立入口，复用前台同构的双 token
    """
    email = login_data.email
    password = login_data.password
    user = await user_service.crud_get_user_by_email_or_none(
        db, email
    )  # user是ORM的User对象

    if user:
        # 检验密码是否正确（无论是否管理员都执行，对齐响应时间）
        password_valid = security.verify_password(password, user.password)
        if password_valid:
            if not user.is_active:
                raise HTTPException(
                    status_code=403,
                    detail="该账户已封禁",
                )

            # 密码已验证、时间已对齐，此刻才做权限判断；
            # 文案与"密码错误"完全一致 —— 不给「枚举管理员账号」留信息差
            if not user.is_superuser:
                raise HTTPException(
                    status_code=401,
                    detail="邮箱或密码错误",
                )

            # ========== 签发与 /user/login 完全同构的双 token ==========
            access_token = security.create_access_token(
                user_data={"email": user.email, "user_uid": str(user.uid)},
            )

            # 我希望每次进入后台都单独登录，所以不再更新刷新令牌
            # refresh_token = security.create_access_token(
            #     user_data={
            #         "email": user.email,
            #         "user_uid": str(user.uid)
            #     }, expiry=timedelta(days=2), refresh=True, )
            # ============================================================

            login_out = AdminLoginOut(
                access_token=access_token,
                user=LoginUserOut(
                    email=user.email,
                    uid=str(user.uid),
                    is_superuser=user.is_superuser,
                ),
            )
            return success_response(data=login_out, message="登录成功")
        else:
            raise HTTPException(
                status_code=401,
                detail="邮箱或密码错误",
            )
    else:
        security.verify_password(password, DUMMY_HASH)  # 纯为对齐时间，返回值弃用
        raise HTTPException(
            status_code=401,
            detail="邮箱或密码错误",
        )


@router.post("/logout", response_model=Envelope[None])
async def logout(
    token_data: dict = Depends(access_token_bearer),
):
    await add_jti_to_blocklist(token_data["jti"])
    return success_response(message="登出成功")


@router.post("/update_user", response_model=Envelope[UserOutModel])
async def update_user(
    user_data: UserUpdateModel,
    db: AsyncSession = Depends(get_database),
    user_identity=Depends(user_checker),
):
    new_user = await user_service.crud_update_user(db, user_data.email, user_data)
    if new_user:
        new_user_out = UserOutModel.model_validate(new_user)
        return success_response(data=new_user_out, message="更新成功")
    else:
        raise UserException()


@router.delete("/delete", response_model=Envelope[None])
async def delete_user(
    email: str,  # 这里不选择路径参数,而是在后台手动输入
    db: AsyncSession = Depends(get_database),
    user_identity=Depends(user_checker),
    user_details=Depends(access_token_bearer),
):
    if user_details["user"]["email"] == email:
        raise HTTPException(status_code=403, detail="不能删除当前登录用户")

    result = await user_service.crud_delete_user(db, email)
    if result:
        return success_response(message="删除成功")
    else:
        raise UserException()


@router.get("/users", response_model=Envelope[AdminUserPageOut])
async def get_users(
    user_identity=Depends(user_checker),
    db: AsyncSession = Depends(get_database),
    page: int = 1,
    page_size: int = 15,
):
    rows, total, page, page_size = await admin_service.get_users_information(
        db, page, page_size
    )

    users_out = []
    for r in rows:
        out = AdminUserOut.model_validate(r.User)
        out.post_count = r.post_count
        out.comment_count = r.comment_count
        out.goods_count = r.goods_count
        users_out.append(out)

    return success_response(
        data={"users": users_out, "total": total, "page": page, "page_size": page_size},
        message="获取成功",
    )


@router.get("/posts", response_model=Envelope[AdminPostsPageOut])
async def get_posts(
    user_identity=Depends(user_checker),
    db: AsyncSession = Depends(get_database),
    page: int = 1,
    page_size: int = 15,
):
    rows, total_posts, page, page_size = await admin_service.get_posts_information(
        db, page, page_size
    )
    posts_out = []
    for r in rows:
        out = AdminPostOut.model_validate(r.Posts)
        out.comment_count = r.comment_count
        out.like_count = r.like_count
        posts_out.append(out)

    return success_response(
        data={
            "posts": posts_out,
            "total": total_posts,
            "page": page,
            "page_size": page_size,
        },
        message="获取成功",
    )


@router.get("/goods", response_model=Envelope[AdminGoodsPageOut])
async def get_goods(
    user_identity=Depends(user_checker),
    db: AsyncSession = Depends(get_database),
    page: int = 1,
    page_size: int = 15,
):
    rows, total_goods, page, page_size = await admin_service.get_goods_information(
        db, page, page_size
    )
    goods_out = []
    for r in rows:
        out = GoodsOutModel.model_validate(r.Goods)
        goods_out.append(out)

    return success_response(
        data={
            "goods": goods_out,
            "total": total_goods,
            "page": page,
            "page_size": page_size,
        },
        message="获取成功",
    )


@router.get("/overview", response_model=Envelope[AdminOverviewOut])
async def get_overview(
    user_identity=Depends(user_checker),
    db: AsyncSession = Depends(get_database),
):
    # ## 为什么不是 a,b,c = await ... 那种元组解构
    # crud 返回的是 dict（键来自 select 里的 label）：解构 dict 拿到的是"键"而不是"值"，
    # 数量对不上还会直接 ValueError。契约是 dict 就用 dict 接 ——
    # 模型字段名与这些键同名，model_validate 按名取值，天然对齐。
    data = await admin_service.get_overview(db)
    return success_response(data=AdminOverviewOut.model_validate(data), message="获取成功")

# routers/admin.py
@router.get("/trends", response_model=Envelope[AdminTrendsOut])
async def get_trends(
        user_identity=Depends(user_checker),
        db: AsyncSession = Depends(get_database),
        days: int = 7,
):
    rows = await admin_service.get_trends(db, days)
    # crud 返回 [{"date","count"}]，在这里转成列式（ECharts 直接吃）
    return success_response(
        data=AdminTrendsOut(
            dates=[r["date"] for r in rows],
            posts=[r["count"] for r in rows],
        ),
        message="获取成功",
    )


@router.get("/distribution", response_model=Envelope[AdminDistributionOut])
async def get_distribution(
        user_identity=Depends(user_checker),
        db: AsyncSession = Depends(get_database),
):
    post_rows, goods_rows = await admin_service.get_categorical_data(db)
    return success_response(
        data=AdminDistributionOut(
            post_categories=[DistItemOut(**r) for r in post_rows],
            goods_classifies=[DistItemOut(**r) for r in goods_rows],
        ),
        message="获取成功",
    )
