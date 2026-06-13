from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from models.model_bookmark import Bookmark
from models.model_posts import Posts


class BookmarkService:
    async def crud_toggle_bookmark(self, db: AsyncSession, post_id: int, user_uid: str):
        """
        收藏/取消收藏（切换操作）
        先检查帖子是否存在
        """
        # 检查帖子
        stmt = select(Posts).where(Posts.id == post_id)
        result = await db.execute(stmt)
        post = result.scalar_one_or_none()
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")

        # 检查是否已收藏
        stmt_bookmark = select(Bookmark).where(Bookmark.post_id == post_id, Bookmark.user_uid == user_uid)
        result = await db.execute(stmt_bookmark)
        existing = result.scalar_one_or_none()

        if existing:
            # 取消收藏
            await db.delete(existing)
            await db.commit()
            return {"bookmarked": False, "message": "取消收藏"}
        else:
            # 收藏
            new_bookmark = Bookmark(post_id=post_id, user_uid=user_uid)
            db.add(new_bookmark)
            await db.commit()
            return {"bookmarked": True, "message": "收藏成功"}

    async def crud_get_user_bookmarks(self, db: AsyncSession, user_uid: str):
        """获取用户收藏的所有帖子id"""
        stmt = select(Bookmark).where(Bookmark.user_uid == user_uid).order_by(Bookmark.created_time.desc())
        result = await db.execute(stmt)
        return result.scalars().all()
