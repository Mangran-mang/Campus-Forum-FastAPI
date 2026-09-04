from datetime import timedelta, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.database_config import get_database

from crud.user import UserService
from crud.token import TokenService

from schemas.user import (
    UserCreateModel, UserUpdateModel, UserLoginModel, UserOutModel,
)
from tools import security
from tools.exceptions import success_response, UserException
from tools.dependencies import (
    AccessTokenBearer, RefreshTokenBearer, get_user_by_token, UserChecker,
)
from config.redis_config import add_jti_to_blocklist

router = APIRouter(prefix="/api/user", tags=["用户管理"])

user_service = UserService()
token_service = TokenService()
access_token_bearer = AccessTokenBearer()
refresh_token_bearer = RefreshTokenBearer()
user_checker = UserChecker(True)

# 因为判断用户是否存在的时间较快，而读哈希密码速度较慢，所以这里用一个假密码来对齐时间
DUMMY_HASH = security.get_password_hash("对齐时间的假密码")


@router.get("/current_user")
async def get_current_user(
        user=Depends(get_user_by_token), ):
    """
    获取当前用户（需登录）
    """
    user_out = UserOutModel.model_validate(user)
    return success_response(data=user_out, message="获取成功")


@router.get("/all")
async def get_all_users(
        db: AsyncSession = Depends(get_database, ), _=Depends(user_checker), ):
    """
    获取所有用户
    """
    # print(f"查询者信息为{user_details}")
    users = await user_service.crud_get_all_users(db)
    users_out = [UserOutModel.model_validate(user) for user in users]
    return success_response(data=users_out, message="获取成功")


@router.post("/add")
async def add_new_user(
        user_data: UserCreateModel, db: AsyncSession = Depends(get_database), ):
    """
    添加用户
    """
    if await user_service.crud_user_exists(db, user_data.email):
        raise HTTPException(status_code=400, detail="用户已存在")

    user = await user_service.crud_add_new_user(db, user_data)
    user_out = UserOutModel.model_validate(user)
    return success_response(data=user_out, message="添加成功")


@router.get("/get/{email}")
async def get_user_by_email(
        email: str,
        db: AsyncSession = Depends(get_database),
        user = Depends(get_user_by_token)
):
    """
    通过邮箱获取用户
    """
    if user.email != email:
        raise HTTPException(status_code=403, detail="无权访问")
    user = await user_service.crud_get_user_by_email(db, email)
    if user:
        user_out = UserOutModel.model_validate(user)
        return success_response(data=user_out, message="获取成功")
    else:
        raise UserException()  # 原先是 return {"code":404,...}，HTTP 却是 200


@router.post("/update")
async def update_user(
        user_data: UserUpdateModel, db: AsyncSession = Depends(get_database, ),
        user_details=Depends(access_token_bearer), ):
    """
    更新用户（仅本人或管理员可操作）
    """
    # 检查权限：只能更新自己的信息，或管理员可以更新任何人
    current_email = user_details["user"]["email"]
    if current_email != user_data.email:
        # 如果不是本人，检查是否为管理员
        current_user = await user_service.crud_get_user_by_email(db, current_email)
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="无权修改其他用户的信息", )

    new_user = await user_service.crud_update_user(db, user_data.email, user_data)
    new_user_out = UserOutModel.model_validate(new_user)
    if new_user:
        return success_response(data=new_user_out, message="更新成功")
    else:
        raise UserException()  # 原先是 return {"code":404,...}，HTTP 却是 200


@router.delete("/delete/{email}")
async def delete_user(
        email: str, db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer), ):
    """
    删除用户（仅本人或管理员可操作）
    """
    current_email = user_details["user"]["email"]
    current_user = await user_service.crud_get_user_by_email(db, current_email)

    # 只能删除自己，或管理员可以删除任何人
    if current_email != email and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权删除其他用户", )

    result = await user_service.crud_delete_user(db, email)
    if result:
        return success_response(message="删除成功")
    else:
        raise UserException()  # 原先是 return {"code":404,...}，HTTP 却是 200


@router.post("/login")
async def login_user(
        login_data: UserLoginModel,
        db: AsyncSession = Depends(get_database), ):
    """
    登录用户，并创建刷新令牌和访问令牌
    """
    email = login_data.email
    password = login_data.password
    user = await user_service.crud_get_user_by_email_or_none(db, email)  # 这里的user是orm模型User对象

    if user:
        # 检验密码是否正确
        password_valid = security.verify_password(password, user.password)
        if password_valid:
            # ==========创建访问令牌==============
            access_token = security.create_access_token(
                user_data={
                    "email": user.email,
                    "user_uid": str(user.uid)
                }, )
            refresh_token = security.create_access_token(
                user_data={
                    "email": user.email,
                    "user_uid": str(user.uid)
                }, expiry=timedelta(days=2), refresh=True, )
            # =================================

            refresh_token_details = security.decode_token(refresh_token)

            # ============将刷新令牌添加到数据库=============
            # 双重保障，这里检测以此，在crud函数中再检测一次，好吧有点没必要但我懒得改了
            orm_token = await token_service.crud_get_token_by_user_uid(db, user.uid)
            if orm_token is None:
                await token_service.crud_add_token(db, refresh_token, refresh_token_details)
            else:
                await token_service.crud_update_token(db, refresh_token, refresh_token_details)
            # =========================================

            # 注意：access_token / refresh_token / user 全部放进 data，
            # 原来平铺在顶层，前端适配时要改成读 res.data.xxx
            return success_response(
                data={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {
                        "email": user.email,
                        "uid": str(user.uid),
                        "is_superuser": user.is_superuser,
                    }
                },
                message="登录成功",
            )
        else:
            raise HTTPException(
                status_code=401, detail="邮箱或密码错误", )
    else:
        password_valid = security.verify_password(password, DUMMY_HASH)  # 对齐时间
        raise HTTPException(
            status_code=401, detail="邮箱或密码错误", )


@router.post("/refresh_token")
async def refresh_token(
        token_data=Depends(refresh_token_bearer),
        db: AsyncSession = Depends(get_database), ):
    """
    使用刷新令牌来实现访问令牌的更新（refresh token 轮换）

    ## 轮换逻辑（2026-09-04 起）
    校验通过后不只发新 access，同时签发一把新 refresh 并覆盖库行：
    - 旧 refresh 的作废不靠额外拉黑——库行被覆盖成新哈希后，
      旧 token 下次再来哈希比对必然失败（单行模型下覆盖即作废）
    - 每把 refresh 只能使用一次 → 泄露的凭证只有一次利用窗口
    - 新 refresh 重新给 2 天 → 轮换自带滑动续期，活跃用户不被踢
    - 代价：双标签页同时刷新时后到者会 401，前端收到后引导重新登录即可（不做宽容窗口）
    """
    token_timestamp = token_data["exp"]  # 拿到令牌过期时间
    # timestamp个方法会把 naive 时间按本地时区解释再转成 UTC 时间戳
    if token_timestamp <= int(datetime.now().timestamp()):  # 如果令牌已过期
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="刷新令牌已过期", )
    else:
        # 如果未过期，则验证是否在数据库中
        orm_token = await token_service.crud_get_token_by_user_uid(
            db, token_data["user"]["user_uid"], )
        if orm_token is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="刷新令牌不存在", )

        # 库中存的是 sha256 哈希，把用户交上来的原始 token 再哈希一次比对：
        # - 只有「当前存库这把」能过，被轮换/新登录顶掉的旧 token 哈希对不上，直接拒绝
        # - 之前只查「有没有这一行」不比对 token，等于谁拿到旧 refresh 都能刷，这是顺手修掉的隐患
        if security.hash_token(token_data["raw_token"]) != orm_token.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌已失效,请重新登录", )

        new_access_token = security.create_access_token(
            user_data=token_data["user"], )
        # ============ 轮换：签发新 refresh 并覆盖库行 ============
        # 旧 refresh 此刻即作废（哈希比对不再通过），前端必须保存返回的新 refresh
        new_refresh_token = security.create_access_token(
            user_data=token_data["user"],
            expiry=timedelta(days=2),
            refresh=True,
        )
        new_refresh_details = security.decode_token(new_refresh_token)
        await token_service.crud_update_token(db, new_refresh_token, new_refresh_details)
        # =====================================================
        return success_response(
            data={
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
            },
            message="刷新成功",
        )


@router.post("/logout")
async def logout_user(
        token_data: dict = Depends(access_token_bearer),
        db: AsyncSession = Depends(get_database), ):
    """
    登出用户
    拿到token中的jti并将其拉黑
    """

    # 拿到现在的时间，用来计算token的理论剩余过期时间
    now_ts = int(datetime.now().timestamp())
    await add_jti_to_blocklist(
        token_data["jti"], expiry=token_data["exp"] - now_ts, )

    # ② 从数据库找出该用户的 refresh token 记录，拉黑其 jti 并删除记录
    # 库里 refresh_token 已是哈希，解不出 jti，所以登出直接用 jti 列 + expire_at 列
    orm_token = await token_service.crud_get_token_by_user_uid(
        db, token_data["user"]["user_uid"], )
    if orm_token:
        if orm_token.jti:
            # expire_at 是 naive datetime，.timestamp() 按本地时区解释，
            # 与原存的 UTC 时间戳一致，用它算剩余存活秒数
            expire_ts = int(orm_token.expire_at.timestamp())
            await add_jti_to_blocklist(
                orm_token.jti, expiry=max(expire_ts - now_ts, 1), )
        await db.delete(orm_token)
        await db.commit()

    return success_response(message="登出成功")
