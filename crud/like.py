from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from models.model_like import Like
from models.model_posts import Posts


class LikeService:
    async def crud_toggle_like(self, db: AsyncSession, post_id: int, user_uid: str):
        """
        点赞/取消点赞（切换操作）
        先检查帖子是否存在
        """
        # 检查帖子
        stmt = select(Posts).where(Posts.id == post_id)
        result = await db.execute(stmt)
        post = result.scalar_one_or_none()
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")

        # 检查是否已点赞
        stmt_like = select(Like).where(Like.post_id == post_id, Like.user_uid == user_uid)
        result = await db.execute(stmt_like)
        existing = result.scalar_one_or_none()

        if existing:
            # 取消点赞
            await db.delete(existing)
            await db.commit()
            return {"liked": False, "message": "取消点赞"}
        else:
            # 点赞
            new_like = Like(post_id=post_id, user_uid=user_uid)
            db.add(new_like)
            await db.commit()
            return {"liked": True, "message": "点赞成功"}

    async def crud_get_like_count(self, db: AsyncSession, post_id: int):
        """获取帖子点赞数"""
        stmt = select(Like).where(Like.post_id == post_id)
        result = await db.execute(stmt)
        likes = result.scalars().all()
        return len(likes)

    async def crud_check_user_liked(self, db: AsyncSession, post_id: int, user_uid: str):
        """检查当前用户是否已点赞"""
        stmt = select(Like).where(Like.post_id == post_id, Like.user_uid == user_uid)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None
