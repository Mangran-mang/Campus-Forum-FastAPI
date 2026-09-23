from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.model_level_config import LevelConfig
from models.model_user import User
from schemas.user import UserCreateModel, UserUpdateModel
from tools import security
from tools.exceptions import UserException


class UserService:
    async def crud_get_all_users(self, db: AsyncSession):
        """
        返回所有用户
        """
        users = select(User)
        result = await db.execute(users)
        return result.scalars().all()

    async def crud_add_new_user(self, db: AsyncSession, user: UserCreateModel):
        """
        创建后返回orm模型User对象
        """
        orm_user = User(**user.model_dump())
        orm_user.password = security.get_password_hash(user.password)
        orm_user.is_superuser = False# 强制默认为非管理员
        orm_user.is_active = True
        db.add(orm_user)
        await db.commit()
        await db.refresh(orm_user)
        return orm_user

    async def crud_get_user_by_email(self, db: AsyncSession, email: str):
        """
        返回orm模型User对象或空
        """
        user = select(User).where(User.email == email)
        result = await db.execute(user)
        user_obj = result.scalar_one_or_none()
        if not user_obj:
            raise UserException()

        return user_obj

    async def crud_get_user_by_email_or_none(
            self, db: AsyncSession, email: str
            ):
        """
        与 crud_get_user_by_email 的区别：查不到返回 None 而不抛异常
        专供登录等需要"自己处理不存在场景"的调用方使用
        """
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


    async def crud_delete_user(self, db: AsyncSession, email: str):
        """
        删除用户
        """
        user = select(User).where(User.email == email)
        result = await db.execute(user)
        user = result.scalar_one_or_none()
        if user:
            await db.delete(user)
            await db.commit()
            return True
        else:
            return False


    async def crud_user_exists(self, db: AsyncSession, email: str):
        """
        检验目标用户是否存在于数据库中
        并返回True或False
        """
        try:
            user = await self.crud_get_user_by_email(db, email)
            return True if user else False
        except UserException:
            return False


    async def crud_update_user(
            self, db: AsyncSession, email: str, user: UserUpdateModel, ):# 遗留问题9,密码修改后无法登录的问题
        """
        更新目标用户的数据
        且只更新传入的字段，忽略空字段
        空字段的实现由pydantic模型的默认值实现
        更新后返回orm模型user对象
        """
        orm_user = await self.crud_get_user_by_email(db, email)
        if orm_user:
            update_data = user.model_dump(exclude_unset=True)  # 获取需要更新的数据实现自适应更新
            for key, value in update_data.items():
                setattr(orm_user, key, value)
            if update_data.get("password"):
                orm_user.password = security.get_password_hash(user.password)
            await db.commit()
            await db.refresh(orm_user)
            return orm_user
        else:
            return None

    async def crud_change_password(
            self, db: AsyncSession, uid: str, old_password: str, new_password: str
    ) -> bool:
        """
        修改密码：先校验原密码，通过后把新密码哈希入库

        ## 与 crud_update_user 的分工
        crud_update_user 管"改资料"（昵称/性别……），密码只是它顺带能改的字段之一；
        本方法管"专门改密码"，比它多一道**原密码校验**的门。
        两者调用的是同一个 security.get_password_hash —— 哈希规则只有一处定义，
        这是修掉"注册加密、更新不加密"那个 bug 时确立的底线：
        同一个字段的落库变换绝不能有两份实现。

        ## 为什么原密码错了返回 401 而不是 403
        401 = 身份没通过验证；403 = 身份通过了但权限不够。原密码不对属于前者。
        另外这里**不需要**像登录那样做防枚举（统一文案 + 对齐时序）：
        能走到这个接口的必定已经持有有效 token，攻击者不靠报错来猜什么。

        ## 不提交会话作废
        本方法只负责改库里的密码。把该用户已签发的 token 一并作废
        （删 token 行 + 拉黑 refresh 的 jti）放在路由层做 ——
        那是"会话"这一侧的事，和密码这一侧职责不同。
        """
        orm_user = await self.crud_get_user_by_uid(db, uid)
        if not orm_user:
            raise UserException()

        if not security.verify_password(old_password, orm_user.password):
            raise HTTPException(status_code=401, detail="原密码不正确")

        orm_user.password = security.get_password_hash(new_password)
        await db.commit()
        return True

    async def crud_get_user_by_uid(self, db: AsyncSession, uid: str):
        """
        通过 uid 获取 ORM 用户对象
        """
        stmt = select(User).where(User.uid == uid)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _compute_level(self, db: AsyncSession, experience: int) -> int:
        """
        根据经验值对照 level_config 推导等级。
        取 min_experience <= 当前经验 中门槛最高的那一级；
        若没有任何等级门槛被满足（经验为 0），返回 0（新手/未分级）。
        """
        stmt = (
            select(LevelConfig.level)
            .where(LevelConfig.min_experience <= experience)
            .order_by(LevelConfig.min_experience.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        level = result.scalar_one_or_none()
        return level if level is not None else 0

    async def crud_get_superusers(self, db: AsyncSession):
        """
        查询所有管理员(is_superuser=True)用户，返回 ORM User 对象列表
        """
        stmt = select(User).where(User.is_superuser == True)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def crud_add_experience(self, db: AsyncSession, uid: str, amount: int):
        """
        原子增加用户经验，并按 level_config 重新计算等级。
        注意：本方法只执行 UPDATE，不提交事务，由调用方统一 commit，
        以便把「发帖/评论」与「经验累加」放进同一个事务。
        """
        # 原子自增经验，避免并发下的 read-modify-write 丢失
        await db.execute(
            update(User).where(User.uid == uid).values(experience=User.experience + amount)
        )
        # 读取最新经验值并推导等级
        result = await db.execute(select(User.experience).where(User.uid == uid))
        experience = result.scalar_one()
        level = await self._compute_level(db, experience)
        await db.execute(
            update(User).where(User.uid == uid).values(level=level)
        )
