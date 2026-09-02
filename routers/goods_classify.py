from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from crud.goods_classify import GoodsClassifyService
from tools.exceptions import success_response

router = APIRouter(prefix='/api/classify', tags=['商品分类'])


@router.get('/get_classify')
async def get_all_classify(db: AsyncSession = Depends(get_database)):
    service = GoodsClassifyService()
    classify_list = await service.get_all_classify(db)
    return success_response(data=classify_list, message="获取成功")


@router.get('/get_classify/{id}')
async def get_classify(id: str, db: AsyncSession = Depends(get_database)):
    service = GoodsClassifyService()
    result = await service.get_goods_classify(db, id)
    if not result:
        raise HTTPException(status_code=404, detail='分类不存在')
    return success_response(data=result, message="获取成功")
