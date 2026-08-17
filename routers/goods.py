from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from crud.goods import GoodsService
from models.model_user import User
from schemas.goods import GoodsCreatePyModel, GoodsUpdatePyModel
from tools.dependencies import AccessTokenBearer, get_user_by_token

access_token_bearer = AccessTokenBearer()

router = APIRouter(
    prefix='/api/goods', tags=['商品'], )

service = GoodsService()


@router.post(
    '/add_goods', )
async def add_goods(
        goods: GoodsCreatePyModel, db: AsyncSession = Depends(get_database),
        user_details=Depends(access_token_bearer), ):
    author_uid = user_details["user"]["user_uid"]
    return await service.add_goods(
        db, goods, author_uid, )


@router.get(
    '/get_goods', )
async def get_all_goods(
        db: AsyncSession = Depends(
            get_database, ), ):
    return await service.get_all_goods(
        db, )


@router.get(
    '/get_goods/{gid}', )
async def get_goods_by_gid(
        gid: str, db: AsyncSession = Depends(get_database, ), ):
    result = await service.get_goods(
        db, gid, )
    if not result:
        raise HTTPException(
            status_code=404, detail='商品不存在', )
    return result


@router.put(
    '/{gid}', )
async def update_goods(
        gid: str, goods: GoodsUpdatePyModel,
        db: AsyncSession = Depends(get_database, ),
        user_details=Depends(access_token_bearer), ):
    orm_user: User = await get_user_by_token(token_details=user_details, db=db)
    return await service.update_goods(
        db, gid, goods, orm_user, )


@router.delete(
    '/{gid}', )
async def delete_goods(
        gid: str, db: AsyncSession = Depends(get_database, ),
        user_details=Depends(access_token_bearer), ):
    orm_user: User = await get_user_by_token(token_details=user_details, db=db)
    await service.delete_goods(
        db, gid, orm_user, )
    return {
        'message': '删除成功'
    }
