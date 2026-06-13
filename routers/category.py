from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.database_config import get_database
from crud.category import CategoryService
from schemas.category import CategoryCreateModel, CategoryUpdateModel
from tools.dependencies import AccessTokenBearer, get_user_by_token, UserChecker

router = APIRouter(prefix="/api/categories", tags=["板块管理"])

category_service = CategoryService()
access_token_bearer = AccessTokenBearer()
superuser_checker = UserChecker(True)


@router.get("/")
async def get_all_categories(
        db: AsyncSession = Depends(get_database),
):
    """获取所有板块（公开）"""
    categories = await category_service.crud_get_all_categories(db)
    return {"code": 200, "message": "获取成功", "data": categories}


@router.get("/{category_id}")
async def get_category(
        category_id: int,
        db: AsyncSession = Depends(get_database),
):
    """获取单个板块详情（公开）"""
    category = await category_service.crud_get_category_by_id(db, category_id)
    return {"code": 200, "message": "获取成功", "data": category}


@router.post("/add")
async def add_category(
        category_data: CategoryCreateModel,
        db: AsyncSession = Depends(get_database),
        _=Depends(superuser_checker),  # 仅管理员
):
    """新增板块（仅管理员）"""
    category = await category_service.crud_add_category(db, category_data)
    return {"code": 200, "message": "新增成功", "data": category}


@router.post("/update/{category_id}")
async def update_category(
        category_id: int,
        category_data: CategoryUpdateModel,
        db: AsyncSession = Depends(get_database),
        _=Depends(superuser_checker),  # 仅管理员
):
    """更新板块（仅管理员）"""
    category = await category_service.crud_update_category(db, category_id, category_data)
    return {"code": 200, "message": "更新成功", "data": category}


@router.delete("/delete/{category_id}")
async def delete_category(
        category_id: int,
        db: AsyncSession = Depends(get_database),
        _=Depends(superuser_checker),  # 仅管理员
):
    """删除板块（仅管理员）"""
    await category_service.crud_delete_category(db, category_id)
    return {"code": 200, "message": "删除成功"}
