from datetime import timedelta,datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.database_config import get_database

from crud.user import UserService
from crud.token import TokenService

from fastapi.responses import JSONResponse
from schemas.user import UserCreateModel, UserUpdateModel,UserLoginModel
from tools import security
from tools.dependencies import AccessTokenBearer, RefreshTokenBearer,get_user_by_token,UserChecker
from config.redis_config import add_jti_to_blocklist

router = APIRouter(prefix="/api/user",tags=["用户管理"])

user_service = UserService()
token_service = TokenService()
access_token_bearer = AccessTokenBearer()
refresh_token_bearer = RefreshTokenBearer()
user_checker = UserChecker(True)

@router.get("/current_user")
async def get_current_user(
        user=Depends(get_user_by_token),
    ):
    """
    获取当前用户（需登录）
    """
    return {"code":200,"message":"获取成功","data":user}

@router.get("/all")
async def get_all_users(
        db: AsyncSession = Depends(get_database, ),
        user_details=Depends(access_token_bearer)
    ):
    """
    获取所有用户
    """
    # print(f"查询者信息为{user_details}")
    users = await user_service.crud_get_all_users(db)
    return {"code":200,"message":"获取成功","data":users}

@router.post("/add")
async def add_new_user(user_data:UserCreateModel,db:AsyncSession=Depends(get_database)):
    """
    添加用户
    """
    if await user_service.crud_user_exists(db,user_data.email):
        raise HTTPException(status_code=400,detail="用户已存在")

    user = await user_service.crud_add_new_user(db,user_data)

    return {"code":200,"message":"添加成功","data":user}

@router.get("/get/{email}")
async def get_user_by_email(email:str,db:AsyncSession=Depends(get_database)):
    """
    通过邮箱获取用户
    """
    user = await user_service.crud_get_user_by_email(db,email)
    if user:
        return {"code":200,"message":"获取成功","data":user}
    else:
        return {"code":404,"message":"用户不存在"}

@router.post("/update")
async def update_user(
        user_data: UserUpdateModel,
        db: AsyncSession = Depends(get_database,),
        user_details=Depends(access_token_bearer)
):
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
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改其他用户的信息"
            )

    new_user = await user_service.crud_update_user(db, user_data.email, user_data)
    if new_user:
        return {"code":200,"message":"更新成功","data":new_user}
    else:
        return {"code":404,"message":"用户不存在"}

@router.delete("/delete/{email}")
async def delete_user(
        email:str,
        db:AsyncSession=Depends(get_database),
        user_details=Depends(access_token_bearer),
):
    """
    删除用户（仅本人或管理员可操作）
    """
    current_email = user_details["user"]["email"]
    current_user = await user_service.crud_get_user_by_email(db, current_email)

    # 只能删除自己，或管理员可以删除任何人
    if current_email != email and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除其他用户"
        )

    result = await user_service.crud_delete_user(db,email)
    if result:
        return {"code":200,"message":"删除成功"}
    else:
        return {"code":404,"message":"用户不存在"}


@router.post("/login")
async def login_user(login_data:UserLoginModel,db:AsyncSession=Depends(get_database)):
    """
    登录用户，并创建刷新令牌和访问令牌
    """
    email = login_data.email
    password = login_data.password
    user = await user_service.crud_get_user_by_email(db,email)# 这里的user是orm模型User对象

    if user:
        # 检验密码是否正确
        password_valid = security.verify_password(password,user.password)
        if password_valid:
            # ==========创建访问令牌==============
            access_token = security.create_access_token(
                user_data= {
                    "email": user.email,
                    "user_uid":str(user.uid)
                }
            )
            refresh_token = security.create_access_token(
                user_data= {
                    "email": user.email,
                    "user_uid":str(user.uid)
                },
                expiry=timedelta(days=2),
                refresh=True
            )
            # =================================

            refresh_token_details = security.decode_token(refresh_token)

            #============将刷新令牌添加到数据库=============
            # 双重保障，这里检测以此，在crud函数中再检测一次，好吧有点没必要但我懒得改了
            orm_token = await token_service.crud_get_token_by_user_uid(db,user.uid)
            if orm_token is None:
                await token_service.crud_add_token(db,refresh_token,refresh_token_details)
            else:
                await token_service.crud_update_token(db,refresh_token,refresh_token_details)
            # =========================================

            return JSONResponse(
                content={
                    "message":"登录成功",
                    "access_token":access_token,
                    "refresh_token":refresh_token,
                    "user":{
                        "email":user.email,
                        "uid":str(user.uid)
                    }
                }
            )
        else:
            raise HTTPException(
                status_code=401,
                detail="邮箱或密码错误"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="邮箱或密码不能为空"
        )

@router.post("/refresh_token")
async def refresh_token(
        token_data=Depends(refresh_token_bearer),
        db: AsyncSession=Depends(get_database)
    ):
    """
    使用刷新令牌来实现访问令牌的更新
    过期的话返回异常，否则就更新访问令牌并返回成功的信息
    本函数只接收刷新令牌
    """
    token_timestamp = token_data["exp"]# 拿到令牌过期时间
    if token_timestamp <= int(datetime.now().timestamp()):# 如果令牌已过期
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="刷新令牌已过期"
        )
    else:
        # 如果未过期，则验证是否在数据库中
        orm_token = await token_service.crud_get_token_by_user_uid(db,token_data["user"]["user_uid"])
        if orm_token is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="刷新令牌不存在"
            )

        new_access_token = security.create_access_token(user_data=token_data["user"])
        return JSONResponse(
            content={
                "message":"刷新成功",
                "access_token":new_access_token
            }
        )

@router.get("/logout")
async def logout_user(
        token_data: dict=Depends(access_token_bearer)
):
    """
    登出用户
    拿到token中的jti并将其拉黑
    """
    await add_jti_to_blocklist(token_data["jti"])
    return JSONResponse(
        content={
            "message":"登出成功"
        },
        status_code=status.HTTP_200_OK
    )


