from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from models.model_goods import Goods
from models.model_goods_classify import GoodsClassify
from models.model_user import User
from schemas.goods import GoodsCreatePyModel, GoodsUpdatePyModel

MAX_ACTIVE_GOODS = 10  # 每个用户最多同时上架 10 个商品


class GoodsService:
    async def get_all_goods(self, db: AsyncSession):
        stmt = select(Goods).options(
            selectinload(Goods.classify_rel),
            selectinload(Goods.author),
        ).order_by(Goods.update_time.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_goods(self, db:AsyncSession,gid:str):
        stmt = select(Goods).options(
            selectinload(Goods.classify_rel),
            selectinload(Goods.author),
        ).where(Goods.gid == gid)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_goods(
            self, db: AsyncSession, goods: GoodsCreatePyModel, author_uid: str
            ):
        # 限制每个用户的在售商品数量
        active_count_stmt = select(Goods).where(
            Goods.author_uid == author_uid,
            Goods.status == "在售",
        )
        active_result = await db.execute(active_count_stmt)
        active_count = len(active_result.scalars().all())
        if active_count >= MAX_ACTIVE_GOODS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"已有 {active_count} 个在售商品，每人最多上架 {MAX_ACTIVE_GOODS} 个，请先下架部分商品后再发布",
            )

        # 检查商品分类是否存在
        classify_result = await db.execute(select(GoodsClassify).where(GoodsClassify.name == goods.classify))
        classify_obj = classify_result.scalar_one_or_none()
        if not classify_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="商品分类不存在", )

        goods_data = goods.model_dump()
        goods_data.pop('classify', None)  # 把前端传的字符串扔掉
        goods_data['classify'] = classify_obj.id  # 换成真正的 ID

        orm_goods = Goods(**goods_data, author_uid=author_uid)
        db.add(orm_goods)
        await db.commit()
        await db.refresh(orm_goods, ["classify_rel", "author"])
        return orm_goods

    async def update_goods(self, db:AsyncSession, gid:str, goods:GoodsUpdatePyModel, user: User):
        orm_goods = await self.get_goods(db, gid)
        if not orm_goods:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在",
            )
        # 只有商品作者或超级管理员才能修改
        if orm_goods.author_uid != user.uid and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限修改此商品",
            )
        update_data = goods.model_dump(exclude_unset=True)

        # 如果传了分类名称，转换为分类ID
        if 'classify' in update_data:
            classify_result = await db.execute(
                select(GoodsClassify).where(GoodsClassify.name == update_data['classify'])
            )
            classify_obj = classify_result.scalar_one_or_none()
            if not classify_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="商品分类不存在",
                )
            update_data['classify'] = classify_obj.id

        for field, value in update_data.items():
            setattr(orm_goods, field, value)
        await db.commit()
        await db.refresh(orm_goods, ["classify_rel", "author"])
        return orm_goods

    async def delete_goods(self, db:AsyncSession, gid:str, user: User):
        orm_goods = await self.get_goods(db, gid)
        if not orm_goods:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在",
            )
        # 只有商品作者或超级管理员才能删除
        if orm_goods.author_uid != user.uid and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限删除此商品",
            )
        await db.delete(orm_goods)
        await db.commit()