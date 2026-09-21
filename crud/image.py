import asyncio
import logging
import uuid
import os
import io
from pathlib import Path

from PIL import Image as PILImage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException

from models.model_goods import Goods
from models.model_image import Image
from models.model_posts import Posts

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE = 2 * 1024 * 1024       # 单张最大 2MB（原始文件）
MAX_IMAGES_PER_TARGET = 5        # 每个帖子/商品最多 5 张
MAX_DIMENSION = 1600             # 长边最大 1600px
JPEG_QUALITY = 80                # JPEG 压缩质量（0-100）
WEBP_QUALITY = 75                # WebP 质量
BASE_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
"""
写起注释就发狠了忘情了停不下来了
好的
__file__是python内置变量，表示当前文件的路径
Path 类是 Python 标准库中的一个类，用于处理文件系统路径
resolve() 方法用于将路径转换为绝对路径，清理掉符号链接
parent 属性用于获取路径的父目录
"""


def _compress_image(content: bytes, content_type: str) -> bytes:
    """压缩图片：限制尺寸 + 降低质量。GIF 原样返回。"""
    if content_type == "image/gif":
        return content  # 不动 GIF

    img = PILImage.open(io.BytesIO(content))
    # content是我们拿到的二进制数据
    # io.BytesIO(content)把二进制数据content加载到内存，然后PILImage.open打开
    # 返回了一个Image对象给img变量

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


async def _ensure_can_upload(
    db: AsyncSession, target_type: str, target_id: str, author_uid: str
) -> None:
    """校验"目标存在、且当前用户是它的作者"

    ## comment
    ### 补的是哪个漏洞（2026-09-21）
    upload_image 原来只检查了 target_type 白名单，**没有检查目标归属** ——
    任何登录用户都能给【别人的】帖子/商品传图；也能给一个根本不存在的
    target_id 传，造出一堆永远没人引用的脏数据。
    这里用一次查询同时解决两件事：目标存不存在 + 你有没有权限。

    ### 为什么把 target_type 的判断也搬到这里
    原来那句白名单检查写在【读完整个文件、还做完了压缩】之后 ——
    只要传个 2MB 的图，就能让对方白白做一次 PIL 解码 + 缩放 + 重编码。
    这类"能不能做"的判断属于【早失败】，必须在读文件之前。

    ### 为什么 target_id 要转 int
    target_id 是 String(36)：为了一个字段同时兼容帖子（整数 id）和商品（36 位 UUID）。
    所以查帖子时必须自己转回整数，转不了说明前端传错了，直接 400。

    ### 为什么先只放开"作者本人"
    管理员管图是另一条路径（delete_image），这里保持权限判断单一。
    将来要放开管理员，给这个函数加一个 is_superuser 参数即可。
    """
    if target_type == "post":
        try:
            post_id = int(target_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="帖子 id 必须是数字")
        stmt = select(Posts.author_uid).where(Posts.id == post_id)
    elif target_type == "goods":
        stmt = select(Goods.author_uid).where(Goods.gid == target_id)
    else:
        # 同时在防目录穿越：target_type 直接参与磁盘路径拼接
        # （subdir = BASE_UPLOAD_DIR / target_type），不拦住就能写任意子目录
        raise HTTPException(status_code=400, detail="目标类型只允许 post 或 goods")

    result = await db.execute(stmt)
    owner_uid = result.scalar_one_or_none()
    if owner_uid is None:
        raise HTTPException(status_code=404, detail="目标不存在")
    if owner_uid != author_uid:
        raise HTTPException(status_code=403, detail="只能给自己的内容上传图片")


class ImageService:

    @staticmethod
    async def upload_image(
        db: AsyncSession,
        file: UploadFile,
        target_type: str,
        target_id: str,
        author_uid: str,
    ) -> Image:
        # 【前置校验】目标类型 + 目标存在 + 归属权限，全部放在读文件之前
        # （原来这些检查散在后面，会让人用一个大文件白耗一次图片解码 + 压缩）
        await _ensure_can_upload(db, target_type, target_id, author_uid)

        # MIME 校验
        if file.content_type not in ALLOWED_MIME:
            raise HTTPException(status_code=400, detail="仅支持 JPEG/PNG/WebP/GIF 格式")

        # 大小校验（压缩前）请求头里有 Content-Length 就先看它，超 2MB 直接拒，根本不用读
        content_length = file.headers.get("content-length")
        if content_length and int(content_length) > MAX_SIZE:
            raise HTTPException(status_code=400, detail="图片原始大小不能超过 2MB")

        #每次读 1MB，边读边累计，超限立刻停
        content = b""
        while True:
            chunk = await file.read(1024 * 1024)  # 每次读 1MB
            if not chunk:
                break
            content += chunk
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
            content = await asyncio.to_thread(_compress_image,content, file.content_type)
        except Exception:
            raise HTTPException(status_code=400, detail="图片处理失败，请确认文件是有效的图片")

        # UUID 重命名 + 按子目录分存
        ext = os.path.splitext(file.filename or ".jpg")[1] or ".jpg"
        # 将文件名拆分成 主文件名 和 扩展名 两部分，返回一个元组
        filename = f"{uuid.uuid4().hex}{ext}"
        # 注：原来这里有一句 target_type 白名单检查（target_type != "post" and != "goods"），
        # 已上移到函数开头的 _ensure_can_upload 里 —— 它属于前置校验，不该等到这里才做。
        subdir = BASE_UPLOAD_DIR / target_type
        # /是运算符重载，而Path类把/定义成了拼接路径
        # Path("uploads") / "post"等价于旧写法 os.path.join("uploads", "post")
        subdir.mkdir(parents=True, exist_ok=True)
        # 第一个参数是父目录不存在的话一起建
        # 第二个参数是目录已存在时不报错
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
    async def delete_images_by_target(
        db: AsyncSession,
        target_type: str,
        target_id: str,
    ) -> int:
        """删除某个目标下的所有图片（数据库记录 + 磁盘文件），返回删除条数

        ## comment
        ### 为什么必须有这个函数
        images 表用的是【多态软关联】（target_type + target_id 两个普通字段），
        **没有外键** —— 所以删帖子/删商品时，数据库不会级联到图片。
        结果就是图片记录和磁盘文件双双变成孤儿：没人能再查到它（帖子都没了），
        但它一直占着磁盘和表行。

        ### 调用时机
        在删目标【之前或之后】调都行 —— 关联靠的是 target_id 的值，
        帖子删了那个数字也还在，照样查得到。这里推荐先调它，事务里的意图更清楚。

        ### 为什么不 commit
        沿用项目里 crud 的约定：只做操作、由调用方统一 commit，
        这样"删图 + 删帖子"才能进同一个事务（要么都成、要么都回滚）。
        """
        result = await db.execute(
            select(Image).where(
                Image.target_type == target_type,
                Image.target_id == target_id,
            )
        )
        images = list(result.scalars().all())

        for image in images:
            filepath = BASE_UPLOAD_DIR / image.target_type / image.filename
            try:
                if filepath.exists():
                    filepath.unlink()
            except OSError:
                # ## 为什么这里吞掉而不是上抛
                # 文件删不掉（权限、被占用）不该挡住"删帖子"这个主业务 ——
                # 留一个孤儿文件，比让用户删不掉帖子要好。
                logging.exception("删除图片文件失败，已跳过: %s", filepath)
            await db.delete(image)

        return len(images)

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
            filepath.unlink()# 在本地删除文件，相对于os.remove()

        await db.delete(image)
        await db.commit()
