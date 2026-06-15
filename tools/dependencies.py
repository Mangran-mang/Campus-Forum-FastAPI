from typing import Optional

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request, HTTPException,Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.database_config import get_database
from tools.security import decode_token
from config.redis_config import is_jti_in_blocklist
from crud.user import UserService
from models.model_user import User

user_service = UserService()

# 作为依赖项，为接口添加认证功能
class TokenBearer(HTTPBearer):
    """
    注入后自动验证请求头,看是否登录
    """

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)# 继承HTTPBearer并改写auto_error,代表了是否返回错误信息

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        """
        调用时，会自动调用这个方法
        首先继承自父类的__call__完成基础校验,比如看他是不是Authorization请求头
        还会根据auto_error来确定是否返回错误信息
        creds.scheme就是请求头中 Bear <Token>中的Bear
        creds.credentials则是<Token>这部分

        在检验token是否有效，并在token无效时抛出异常

        本函数最终返回的是解码后的token
        """
        creds = await super().__call__(request)# 为什么要写个request，是把参数给父类了？
        token = creds.credentials# creds是什么
        token_data = decode_token(token)

        if creds:
            if self.token_valid(token_data):

                self.verify_token_data(token_data)

                # 使用redis缓存检查JTI是否在黑名单中
                if await is_jti_in_blocklist(token_data["jti"]):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "错误信息":"用户认证信息已过期或无效",
                            "提示信息":"请获取访问令牌重新尝试访问"
                                }
                    )

                return token_data

            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="用户认证信息已过期或无效",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="请先尝试登录",
            )

    def token_valid(self, token_data:Optional[dict]) -> bool:
        """
        验证令牌数据是否为空
        返回True或False
        """
        # token_data = decode_token(token)
        return True if token_data is not None else False

    def verify_token_data(self,token_data):
        """
        强制子类重写此函数
        以此验证指定类型的令牌
        """
        raise NotImplementedError("请在子类中覆盖此验证函数")

class AccessTokenBearer(TokenBearer):
    """
    继承TokenBearer类，验证访问令牌
    """
    def verify_token_data(self,token_data:dict):
        if token_data and token_data.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="这似乎是刷新令牌,请重新尝试使用访问令牌",
            )
class RefreshTokenBearer(TokenBearer):
    """
    继承TokenBearer类，验证刷新令牌
    """
    def verify_token_data(self,token_data:dict):
        if token_data and not token_data.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="这似乎是访问令牌,请重新尝试使用刷新令牌",
            )

async def get_user_by_token(
        token_details: dict = Depends(AccessTokenBearer()),
        db: AsyncSession = Depends(get_database)
):
    """
    通过token拿到用户email
    再通过crud模块中的用户模块，查找具体用户
    返回具体的用户
    """
    user_email = token_details["user"]["email"]
    user = await user_service.crud_get_user_by_email(db,user_email)
    return user

class UserChecker:
    """
    用户权限检查类
    对token进行检查并做出判断
    对某一权限的用户做出限制
    """
    def __init__(self,is_allow:bool):
        """
        is_allow: True表示只允许管理员，False表示允许所有用户
        """
        self.is_allow = is_allow

    def __call__(self,user:User = Depends(get_user_by_token)):
        # 如果 is_allow=False，允许所有登录用户
        if not self.is_allow:
            return True
        # 如果 is_allow=True，只允许管理员
        if user.is_superuser:
            return True
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="普通用户无权限访问"
            )