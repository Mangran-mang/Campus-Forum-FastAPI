from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.model_token import Token
from tools.security import hash_token

class TokenService:
    """
    本类只用来增和改token
    token模型并不是手写的，也不是pydantic模型，而是我们拿到的解密后的token字典！！！

    ## 落库安全约定（2026-09-03 起）
    refresh_token 列只存 sha256(token) 的单向哈希，绝不存原始 token：
    - 数据库泄露（SQL注入/备份泄露/接口误吐字段）时攻击者拿不到可用凭证
    - 验证靠「再哈希比对」，不需要把哈希还原成原文，所以客户端始终拿原始 token，前端零改动
    - jti 列单独存，供登出时拉黑 Redis 黑名单（库里已是哈希，解不出 jti，必须单独存）
    """
    async def crud_add_token(self,db:AsyncSession,token:str,token_data:dict):
        """
        首先，这个业务不会直接由前端来写
        而是在路由函数中，拿路由函数传过来的token中的信息来完成业务
        不用担心uid是手写什么的，而是有uid才会调用这里的函数

        添加token需要user_uid,refresh_token哈希,expire_at,jti，以及未解码的token
        token 是原始 refresh token（调用方传入），落库前在此处转成 sha256
        """
        # =================判断该用户是否已经存在token====================
        orm_token = await self.crud_get_token_by_user_uid(db,token_data["user"]["user_uid"])
        if orm_token is not None:
            raise HTTPException(status_code=400,detail="该用户已存在token")
        #========================================================
        expire_timestamp = token_data["exp"]

        new_token = Token(
            refresh_token = hash_token(token),# 只存单向哈希，原始 token 只存在于客户端与内存
            jti = token_data["jti"],
            expire_at = datetime.fromtimestamp(expire_timestamp),# 将时间戳转为时间
            user_uid = token_data["user"]["user_uid"]
        )
        db.add(new_token)
        await db.commit()
        await db.refresh(new_token)
        return new_token

    async def crud_get_token_by_user_uid(self,db:AsyncSession,user_uid:str):
        """
        需要参数：数据库，user_uid
        通过用户uid获取ORM类token
        返回token模型或None
        """
        orm_token = select(Token).where(Token.user_uid == user_uid)
        result = await db.execute(orm_token)
        return result.scalar_one_or_none()

    async def crud_update_token(self,db:AsyncSession,token:str,token_data:dict):
        """
        传入的参数token_data是解码后的字典
        更新token
        返回orm模型token
        """
        # =================判断该用户是否已经存在token====================
        orm_token = await self.crud_get_token_by_user_uid(db,token_data["user"]["user_uid"])
        if orm_token is None:
            raise HTTPException(status_code=400,detail="该用户不存在token")
        # ========================================================
        expire_timestamp = token_data["exp"]

        current_token = {
            "refresh_token":hash_token(token),# 同 crud_add_token，只落哈希
            "jti":token_data["jti"],
            "expire_at":datetime.fromtimestamp(expire_timestamp),
            "user_uid":token_data["user"]["user_uid"]
        }

        for key,value in current_token.items():
            setattr(orm_token,key,value)

        await db.commit()
        await db.refresh(orm_token)
        return orm_token