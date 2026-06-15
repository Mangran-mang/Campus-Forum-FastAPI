from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.functions import func

from models import User
from models.model_comments import Comments
from models.model_posts import Posts

from schemas.comments import CommentsCreateModel
from tools.exceptions import CommentsException

class CommentsService:
    async def crud_add_new_comment_into_post(
            self,
            db: AsyncSession,
            comment: CommentsCreateModel,
            post_id: int,
            commenter_uid: str
    ):
        """
        发表评论（支持楼中楼回复）
        如果 comment.parent_id 不为空，则校验父评论属于同一个帖子
        """
        # 如果指定了父评论，校验存在性
        if comment.parent_id is not None:
            parent = await self.crud_get_comment_by_comment_id(db, comment.parent_id)
            if parent.post_id != post_id:
                raise HTTPException(status_code=400, detail="父评论不属于该帖子")

        orm_comment = Comments(
            content=comment.content,
            author_uid=commenter_uid,
            post_id=post_id,
            parent_id=comment.parent_id
        )
        db.add(orm_comment)
        await db.commit()
        await db.refresh(orm_comment)
        # 同时加载 author 信息
        await db.refresh(orm_comment, ["author"])
        return orm_comment

    async def crud_get_comments_by_post_id(
            self,
            db: AsyncSession,
            post_id: int,
            page: int = 1,
            page_size: int = 10
    ):
        """
        返回某个文章下的所有一级评论（含各自的楼中楼回复）
        按时间倒序排列
        """
        # 查该帖子的一级评论总数
        stmt_count = select(func.count()).where(
            Comments.post_id == post_id,
            Comments.parent_id.is_(None)  # 只统计一级评论
        )
        result = await db.execute(stmt_count)
        total = result.scalar_one_or_none()

        offset = (page - 1) * page_size

        # 查一级评论（parent_id 为 null）
        stmt = (
            select(Comments)
            .where(Comments.post_id == post_id, Comments.parent_id.is_(None))
            .options(
                selectinload(Comments.author),
                selectinload(Comments.replies).selectinload(Comments.author),  # 子回复也加载作者
            )
            .order_by(Comments.created_time.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        comments_list = result.scalars().all()
        return total, comments_list

    async def crud_get_comment_by_comment_id(self, db: AsyncSession, comment_id: int):
        """
        通过评论id获取ORM评论
        """
        stmt = select(Comments).where(Comments.id == comment_id)
        result = await db.execute(stmt)
        comment_obj = result.scalar_one_or_none()
        if not comment_obj:
            raise CommentsException()
        return comment_obj

    async def crud_delete_comment_by_comment_id(
            self,
            db: AsyncSession,
            comment_id: int,
            current_user_uid: str,
            user: User
    ):
        """
        删除某个评论
        删评需要检查是评论者本人还是管理员
        """
        orm_comment = await self.crud_get_comment_by_comment_id(db, comment_id)
        if orm_comment is None:
            raise HTTPException(status_code=404, detail="该评论不存在")
        if orm_comment.author_uid != current_user_uid and not user.is_superuser:
            raise HTTPException(status_code=403, detail="没有权限删除该评论")

        stmt = delete(Comments).where(Comments.id == comment_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
