from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.functions import func

from models import User
from models.model_goods_comment import GoodsComment
from schemas.goods_comment import GoodsCommentCreateModel


class GoodsCommentService:
    async def crud_add_comment(
            self,
            db: AsyncSession,
            comment: GoodsCommentCreateModel,
            goods_gid: str,
            commenter_uid: str
    ):
        """发表评论（支持楼中楼回复）"""
        # 如果指定了父评论，校验存在性
        if comment.parent_id is not None:
            parent = await self.crud_get_comment_by_id(db, comment.parent_id)
            if parent.goods_gid != goods_gid:
                raise HTTPException(status_code=400, detail="父评论不属于该商品")

        orm_comment = GoodsComment(
            content=comment.content,
            author_uid=commenter_uid,
            goods_gid=goods_gid,
            parent_id=comment.parent_id
        )
        db.add(orm_comment)
        await db.commit()
        await db.refresh(orm_comment)
        await db.refresh(orm_comment, ["author"])
        return orm_comment

    async def crud_get_comments_by_goods(
            self,
            db: AsyncSession,
            goods_gid: str,
            page: int = 1,
            page_size: int = 10
    ):
        """返回某个商品下的所有一级评论（含各自的楼中楼回复）"""
        stmt_count = select(func.count()).where(
            GoodsComment.goods_gid == goods_gid,
            GoodsComment.parent_id.is_(None)
        )
        result = await db.execute(stmt_count)
        total = result.scalar_one_or_none()

        offset = (page - 1) * page_size
        stmt = (
            select(GoodsComment)
            .where(GoodsComment.goods_gid == goods_gid, GoodsComment.parent_id.is_(None))
            .options(
                selectinload(GoodsComment.author),
                selectinload(GoodsComment.replies).selectinload(GoodsComment.author),
            )
            .order_by(GoodsComment.created_time.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        comments_list = result.scalars().all()
        return total, comments_list

    async def crud_get_comment_by_id(self, db: AsyncSession, comment_id: int):
        stmt = select(GoodsComment).where(GoodsComment.id == comment_id)
        result = await db.execute(stmt)
        comment_obj = result.scalar_one_or_none()
        if not comment_obj:
            raise HTTPException(status_code=404, detail="评论不存在")
        return comment_obj

    async def crud_delete_comment(
            self,
            db: AsyncSession,
            comment_id: int,
            current_user_uid: str,
            user: User
    ):
        orm_comment = await self.crud_get_comment_by_id(db, comment_id)
        if orm_comment.author_uid != current_user_uid and not user.is_superuser:
            raise HTTPException(status_code=403, detail="没有权限删除该评论")

        stmt = delete(GoodsComment).where(GoodsComment.id == comment_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
