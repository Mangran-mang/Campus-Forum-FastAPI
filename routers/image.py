from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from config.database_config import get_database
from crud.image import ImageService
from schemas.common import Envelope
from schemas.image import ImageOut
from tools.dependencies import AccessTokenBearer
from tools.exceptions import success_response

access_token_bearer = AccessTokenBearer()

router = APIRouter(prefix="/api", tags=["图片"])


@router.post("/upload/{target_type}/{target_id}", response_model=Envelope[ImageOut])
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
    # 原来这里手拼 {"id":..., "filename":..., "target_type":...}，
    # 现在直接把 ORM 对象交给 ImageOut 即可——效果一样，少一处要同步维护的字段列表
    return success_response(data=image, message="上传成功")


@router.get("/images/{target_type}/{target_id}", response_model=Envelope[list[ImageOut]])
async def get_images(
    target_type: str,
    target_id: str,
    db: AsyncSession = Depends(get_database),
):
    images = await ImageService.get_images(db, target_type, target_id)
    return success_response(data=images, message="获取成功")


@router.delete("/images/{image_id}", response_model=Envelope[None])
async def delete_image(
    image_id: int,
    db: AsyncSession = Depends(get_database),
    user_details=Depends(access_token_bearer),
):
    """删除图片

    没有数据可返回，data 是 None。
    """
    author_uid = user_details["user"]["user_uid"]
    await ImageService.delete_image(db, image_id, author_uid)
    return success_response(message="图片已删除")
