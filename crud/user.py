from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
            self, db: AsyncSession, email: str, user: UserUpdateModel, ):
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
            await db.commit()
            await db.refresh(orm_user)
            return orm_user
        else:
            return None
