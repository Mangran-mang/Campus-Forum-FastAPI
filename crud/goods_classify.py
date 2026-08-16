from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.model_goods_classify import GoodsClassify


class GoodsClassifyService:
    """
    手动添加表中商品的分类数据
    """
    async def get_all_classify(self, db: AsyncSession):
        stmt = select(GoodsClassify)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_goods_classify(self, db:AsyncSession,id:str):
        stmt = select(GoodsClassify).where(GoodsClassify.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
