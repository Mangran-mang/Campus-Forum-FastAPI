from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from crud.image import ImageService
from tools.dependencies import AccessTokenBearer

access_token_bearer = AccessTokenBearer()

router = APIRouter(prefix="/api", tags=["图片"])


@router.post("/upload/{target_type}/{target_id}")
async def upload_image(
    target_type: str,
    target_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_database),
    user_details=Depends(access_token_bearer),
):
    author_uid = user_details["user"]["user_uid"]
    image = await ImageService.upload_image(
        db, file, target_type, target_id, author_uid
    )
    return {"code": 200, "data": {"id": image.id, "filename": image.filename, "target_type": image.target_type}}


@router.get("/images/{target_type}/{target_id}")
async def get_images(
    target_type: str,
    target_id: str,
    db: AsyncSession = Depends(get_database),
):
    images = await ImageService.get_images(db, target_type, target_id)
    return {
        "code": 200,
        "data": [{"id": img.id, "filename": img.filename, "target_type": img.target_type} for img in images],
    }


@router.delete("/images/{image_id}")
async def delete_image(
    image_id: int,
    db: AsyncSession = Depends(get_database),
    user_details=Depends(access_token_bearer),
):
    author_uid = user_details["user"]["user_uid"]
    await ImageService.delete_image(db, image_id, author_uid)
    return {"code": 200, "message": "图片已删除"}
