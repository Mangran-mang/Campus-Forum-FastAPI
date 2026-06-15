from fastapi import HTTPException
from sqlalchemy import select, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.functions import func
from starlette import status

from models import User
from models.model_posts import Posts
from schemas.posts import PostsCreateModel, PostsUpdateModel
from tools.exceptions import PostException


class PostService:
    async def crud_add_new_post(self,db:AsyncSession,post:PostsCreateModel):
        orm_post = Posts(**post.model_dump())
        db.add(orm_post)
        await db.commit()
        await db.refresh(orm_post)
        # 加载关联的作者信息
        await db.refresh(orm_post, ["author"])
        return orm_post

    async def crud_get_posts_list(
            self,
            db:AsyncSession,
            page:int=1,
            page_size:int=10,
            author_uid:str=None,
            category_id:int=None,
            current_user_uid:str=None
            ):
        """
        获取帖子列表
        拿到总列表数，以确定是否还有更多帖子
        如果没有指定作者的话，直接查所有帖子，并返回按创建时间排序好的帖子
        返回找到的帖子总数和查到的帖子的列表

        可见性规则：
        - 公开帖子所有人可见
        - 私密帖子仅作者自己可见
        """
        stmt = select(Posts).options(
            selectinload(Posts.author),
            selectinload(Posts.category)
        ).order_by(Posts.is_top.desc(), Posts.created_time.desc())  # 置顶在前，按时间排序
        skip = (page -1)*page_size

        # 构建可见性条件：公开帖子 或 当前用户自己的私密帖子
        if current_user_uid:
            visibility = or_(Posts.is_public == True, Posts.author_uid == current_user_uid)
        else:
            visibility = Posts.is_public == True

        # 按作者筛选
        if author_uid is not None:
            stmt = stmt.where(Posts.author_uid == author_uid)
            stmt_count = select(func.count()).where(Posts.author_uid == author_uid)
        else:
            stmt_count = select(func.count())

        # 按板块筛选
        if category_id is not None:
            stmt = stmt.where(Posts.category_id == category_id)
            stmt_count = stmt_count.where(Posts.category_id == category_id)

        # 应用可见性条件
        stmt = stmt.where(visibility)
        stmt_count = stmt_count.where(visibility)

        count_result = await db.execute(stmt_count)
        total = count_result.scalar_one_or_none()

        stmt = stmt.offset(skip).limit(page_size)

        result = await db.execute(stmt)
        post_list = result.scalars().all()
        return total, post_list

    async def crud_get_post_details_by_id(self,db:AsyncSession,post_id:int,current_user_uid:str):
        """
        通过id找到具体帖子
        根据帖子是否隐藏与当前用户是否是作者来决定是否显示
        返回的是一个ORM模型
        """
        stmt = select(Posts).options(
            selectinload(Posts.author),
            selectinload(Posts.category)
        ).where(Posts.id == post_id)
        result = await db.execute(stmt)
        post_detail = result.scalar_one_or_none()
        # 先检查有没有这个帖子
        if not post_detail:
            raise PostException("帖子异常","不存在当前查找的帖子")

        if post_detail.is_public or post_detail.author_uid == current_user_uid:
            return post_detail
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="无权限查看此帖子")

    async def crud_update_post(self,
            db:AsyncSession,
            post_id:int,
            post:PostsUpdateModel,
            user: User
    ):
        """
        与删除业务类似
        """
        orm_post = await self.crud_get_post_details_by_id(db,post_id,user.uid)
        if orm_post is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="帖子不存在")

        if orm_post.author_uid != user.uid and not user.is_superuser:# 如果用户不是管理员，和用户不是作者，则无权限修改
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="无权限修改此帖子")

        update_data = post.model_dump(exclude_unset= True)
        for key,value in update_data.items():
            setattr(orm_post,key,value)

        await db.commit()
        await db.refresh(orm_post)
        return orm_post



    async def crud_delete_post(self,db:AsyncSession,post_id:int,user: User):
        """
        删除帖子
        但要求是贴主或管理员身份

        将在路由函数中先拿到用户
        拿用户的方法是dependencies的get_user_by_token
        通过token拿用户
        然后再把User传进来拿uid
        """
        orm_post = await self.crud_get_post_details_by_id(db,post_id,user.uid)
        if orm_post is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="帖子不存在"
                )

        if orm_post.author_uid != user.uid and not user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="无权限删除此帖子")

        stmt = delete(Posts).where(Posts.id == post_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount >0
