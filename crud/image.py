import uuid
import os
import io
from pathlib import Path

from PIL import Image as PILImage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException

from models.model_image import Image

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE = 2 * 1024 * 1024       # 单张最大 2MB（原始文件）
MAX_IMAGES_PER_TARGET = 5        # 每个帖子/商品最多 5 张
MAX_DIMENSION = 1600             # 长边最大 1600px
JPEG_QUALITY = 80                # JPEG 压缩质量（0-100）
WEBP_QUALITY = 75                # WebP 质量
BASE_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"


def _compress_image(content: bytes, content_type: str) -> bytes:
    """压缩图片：限制尺寸 + 降低质量。GIF 原样返回。"""
    if content_type == "image/gif":
        return content  # 不动 GIF

    img = PILImage.open(io.BytesIO(content))

    # 转换为 RGB（JPEG 不支持 RGBA/P）
    if img.mode in ("RGBA", "P", "LA"):
        has_alpha = img.mode in ("RGBA", "LA")# 判断是否真带透明通道
        if content_type == "image/jpeg":
            img = img.convert("RGB")# JPEG 不支持透明 → 丢掉
        elif content_type == "image/webp":
            # WebP 保留透明
            pass
        else:
            # PNG → JPEG（丢弃透明通道更省空间）
            img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # 限制尺寸
    w, h = img.size
    if w > MAX_DIMENSION or h > MAX_DIMENSION:
        ratio = MAX_DIMENSION / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), PILImage.LANCZOS)

    # 编码输出
    out = io.BytesIO()#把压缩结果写到哪。写到内存而不是磁盘，避免中间文件
    if content_type == "image/jpeg":
        fmt = "JPEG"
        opts = {"quality": JPEG_QUALITY, "optimize": True}
    elif content_type == "image/webp":
        fmt = "WEBP"
        opts = {"quality": WEBP_QUALITY}
    else:
        # PNG
        fmt = "PNG"
        opts = {"optimize": True}

    img.save(out, format=fmt, **opts) #  Pillow 把压缩后的内容"写"进 out
                                                                 #   （此刻 out 内部：JPEG编码后的二进制数据）
    return out.getvalue()# 把 out 里存的 bytes 取出来


class ImageService:

    @staticmethod
    async def upload_image(
        db: AsyncSession,
        file: UploadFile,
        target_type: str,
        target_id: str,
        author_uid: str,
    ) -> Image:
        # MIME 校验
        if file.content_type not in ALLOWED_MIME:
            raise HTTPException(status_code=400, detail="仅支持 JPEG/PNG/WebP/GIF 格式")

        # 大小校验（压缩前）
        content = await file.read()
        if len(content) > MAX_SIZE:
            raise HTTPException(status_code=400, detail="图片原始大小不能超过 2MB")

        # 数量限制
        result = await db.execute(
            select(Image).where(
                Image.target_type == target_type,
                Image.target_id == target_id,
            )
        )
        existing = result.scalars().all()
        if len(existing) >= MAX_IMAGES_PER_TARGET:
            raise HTTPException(status_code=400, detail=f"最多上传 {MAX_IMAGES_PER_TARGET} 张图片")

        # 压缩图片
        try:
            content = _compress_image(content, file.content_type)
        except Exception:
            raise HTTPException(status_code=400, detail="图片处理失败，请确认文件是有效的图片")

        # UUID 重命名 + 按子目录分存
        ext = os.path.splitext(file.filename or ".jpg")[1] or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        subdir = BASE_UPLOAD_DIR / target_type#target_type是目标路径
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / filename).write_bytes(content)

        # 写入数据库（filename 不含子目录，前端拼接时用 target_type）
        sort_order = len(existing)
        image = Image(
            filename=filename,
            target_type=target_type,
            target_id=target_id,
            author_uid=author_uid,
            sort_order=sort_order,
        )
        db.add(image)
        await db.commit()
        await db.refresh(image)
        return image

    @staticmethod
    async def get_images(
        db: AsyncSession,
        target_type: str,
        target_id: str,
    ) -> list[Image]:
        result = await db.execute(
            select(Image)
            .where(
                Image.target_type == target_type,
                Image.target_id == target_id,
            )
            .order_by(Image.sort_order)
        )
        return list(result.scalars().all())

    @staticmethod
    async def delete_image(
        db: AsyncSession,
        image_id: int,
        author_uid: str,
    ) -> None:
        result = await db.execute(select(Image).where(Image.id == image_id))
        image = result.scalar_one_or_none()
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")
        if image.author_uid != author_uid:
            raise HTTPException(status_code=403, detail="无权删除此图片")

        # 删除磁盘文件（按子目录找）
        filepath = BASE_UPLOAD_DIR / image.target_type / image.filename
        if filepath.exists():
            filepath.unlink()

        await db.delete(image)
        await db.commit()
