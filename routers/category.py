from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.database_config import get_database
from crud.category import CategoryService
from schemas.category import CategoryCreateModel, CategoryUpdateModel, CategoryOut
from schemas.common import Envelope
from tools.dependencies import AccessTokenBearer, get_user_by_token, UserChecker
from tools.exceptions import success_response

router = APIRouter(prefix="/api/categories", tags=["板块管理"])

category_service = CategoryService()
access_token_bearer = AccessTokenBearer()
superuser_checker = UserChecker(True)


@router.get("/", response_model=Envelope[list[CategoryOut]])
async def get_all_categories(
        db: AsyncSession = Depends(get_database),
):
    """获取所有板块（公开）"""
    categories = await category_service.crud_get_all_categories(db)
    return success_response(data=categories, message="获取成功")


@router.get("/{category_id}", response_model=Envelope[CategoryOut])
async def get_category(
        category_id: int,
        db: AsyncSession = Depends(get_database),
):
    """获取单个板块详情（公开）

    找不到时 crud 会抛异常（交给全局处理器），所以这里 data 不会是 None。
    """
    category = await category_service.crud_get_category_by_id(db, category_id)
    return success_response(data=category, message="获取成功")


@router.post("/add", response_model=Envelope[CategoryOut])
async def add_category(
        category_data: CategoryCreateModel,
        db: AsyncSession = Depends(get_database),
        _=Depends(superuser_checker),  # 仅管理员
):
    """新增板块（仅管理员）"""
    category = await category_service.crud_add_category(db, category_data)
    return success_response(data=category, message="新增成功")


@router.post("/update/{category_id}", response_model=Envelope[CategoryOut])
async def update_category(
        category_id: int,
        category_data: CategoryUpdateModel,
        db: AsyncSession = Depends(get_database),
        _=Depends(superuser_checker),  # 仅管理员
):
    """更新板块（仅管理员）"""
    category = await category_service.crud_update_category(db, category_id, category_data)
    return success_response(data=category, message="更新成功")


@router.delete("/delete/{category_id}", response_model=Envelope[None])
async def delete_category(
        category_id: int,
        db: AsyncSession = Depends(get_database),
        _=Depends(superuser_checker),  # 仅管理员
):
    """删除板块（仅管理员）

    没有数据可返回，所以 data 是 None —— Envelope[None] 正好表达"这里不该有 data"。
    """
    await category_service.crud_delete_category(db, category_id)
    return success_response(message="删除成功")
