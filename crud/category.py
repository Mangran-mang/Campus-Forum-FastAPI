from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from models.model_category import Category
from schemas.category import CategoryCreateModel, CategoryUpdateModel


class CategoryService:
    async def crud_get_all_categories(self, db: AsyncSession):
        """获取所有板块"""
        stmt = select(Category).order_by(Category.sort_order.asc(), Category.id.asc())
        result = await db.execute(stmt)
        return result.scalars().all()

    async def crud_get_category_by_id(self, db: AsyncSession, category_id: int):
        """通过id获取板块"""
        stmt = select(Category).where(Category.id == category_id)
        result = await db.execute(stmt)
        category = result.scalar_one_or_none()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="板块不存在")
        return category

    async def crud_add_category(self, db: AsyncSession, category: CategoryCreateModel):
        """新增板块（管理员操作）"""
        orm_category = Category(**category.model_dump())
        db.add(orm_category)
        await db.commit()
        await db.refresh(orm_category)
        return orm_category

    async def crud_update_category(self, db: AsyncSession, category_id: int, category: CategoryUpdateModel):
        """更新板块（管理员操作）"""
        orm_category = await self.crud_get_category_by_id(db, category_id)
        update_data = category.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(orm_category, key, value)
        await db.commit()
        await db.refresh(orm_category)
        return orm_category

    async def crud_delete_category(self, db: AsyncSession, category_id: int):
        """删除板块（管理员操作）"""
        orm_category = await self.crud_get_category_by_id(db, category_id)
        await db.delete(orm_category)
        await db.commit()
        return True
