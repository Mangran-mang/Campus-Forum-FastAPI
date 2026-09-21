from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.functions import func
from starlette import status

from crud.image import ImageService
from crud.user import UserService
from models import User
from models.model_posts import Posts
from schemas.posts import PostsCreateModel, PostsUpdateModel
from tools.exceptions import PostException


class PostService:
    async def crud_add_new_post(self,db:AsyncSession,post:PostsCreateModel):
        orm_post = Posts(**post.model_dump())
        db.add(orm_post)
        await db.flush()  # 先落库拿到 id，但暂不提交
        # 发帖奖励：作者经验 +3，并重新计算等级（与发帖同一事务）
        user_service = UserService()
        await user_service.crud_add_experience(db, orm_post.author_uid, 3)
        await db.commit()
        await db.refresh(orm_post)
        # 加载关联的作者与板块（author 已包含最新经验/等级）
        # ## 为什么必须把 category 也加载上
        # 路由返回的是 PostOut，里面有 category 字段。
        # 关系没预加载时，Pydantic 读它会触发异步懒加载 → MissingGreenlet → 500。
        # （加 response_model 之前不会暴露：jsonable_encoder 走的是 vars()，
        #   未加载的关系根本不在 __dict__ 里，表现为"字段静默缺失"而不是报错。）
        await db.refresh(orm_post, ["author", "category"])
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

    async def crud_get_post_details_by_id(self,db:AsyncSession,post_id:int,current_user_uid:str,is_superuser:bool=False):
        """
        通过id找到具体帖子
        根据帖子是否隐藏与当前用户是否是作者/管理员来决定是否显示
        返回的是一个帖子ORM模型
        """
        stmt = select(Posts).options(
            selectinload(Posts.author),
            selectinload(Posts.category)
        ).where(Posts.id == post_id)
        result = await db.execute(stmt)
        post_detail = result.scalar_one_or_none()
        # 先检查有没有这个帖子
        if not post_detail:
            raise PostException("不存在当前查找的帖子")

        if is_superuser or post_detail.is_public or post_detail.author_uid == current_user_uid:
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
        orm_post = await self.crud_get_post_details_by_id(db,post_id,user.uid,is_superuser=user.is_superuser)
        if orm_post is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="帖子不存在")

        if orm_post.author_uid != user.uid and not user.is_superuser:# 如果用户不是管理员，和用户不是作者，则无权限修改
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="无权限修改此帖子")

        update_data = post.model_dump(exclude_unset= True)
        for key,value in update_data.items():
            setattr(orm_post,key,value)

        # 手动记录编辑时间
        # ## 为什么是手动赋值而不是靠模型的 onupdate
        # 本表有"浏览一次就 UPDATE 一次 view_count"的业务（get_post_by_id），
        # 而 onupdate 是"该行发生任何 UPDATE 就触发"——那样 updated_time 会变成
        # "最后被浏览时间"。所以模型的 updated_time 不设 onupdate，
        # 只有真正编辑时才在这里显式写一次。
        orm_post.updated_time = datetime.now()

        await db.commit()
        # ## refresh 必须带关系名
        # 不带 attribute_names 的 refresh 会把【所有属性】包括关系全部过期，
        # 之后读 author / category 就会触发异步懒加载 → MissingGreenlet → 500。
        # 而且上面已经 commit 过（expire_on_commit=False），列属性本来就是最新的，
        # 这里只需要把两个关系重新加载一遍。
        await db.refresh(orm_post, ["author", "category"])
        return orm_post

    async def crud_set_post_top(self, db: AsyncSession, post_id: int, is_top: bool):
        """
        置顶 / 取消置顶帖子（仅供管理员接口调用）

        ## comment
        ### 为什么不复用 crud_update_post
        crud_update_post 走的是 PostsUpdateModel + setattr 那一套，设计目标是"改帖子内容"。
        把置顶拆出来单独写，可以避免以后又把管理属性混回用户能提交的模型里
        —— 今天 is_top 那个漏洞就是这么长出来的。
        ### 为什么不 refresh
        - 关系（author / category）在 select 时已用 selectinload 加载好
        - 列属性：is_top 是刚 setattr 的，本来就是新值；
          commit 时 expire_on_commit=False，属性不会被过期
        所以 refresh 是多余的一次查询。而且特别注意：
        【不带关系名的 refresh(orm) 会把关系也一并过期】，
        之后读 author / category 就变成异步懒加载 → MissingGreenlet → 500。
        ### 为什么不改 updated_time
        updated_time 的语义是"最后【编辑】时间"（内容被改过）。
        置顶没改内容，不该污染它 —— 这也正是它没有 onupdate 的原因。
        """
        stmt = select(Posts).options(
            selectinload(Posts.author),
            selectinload(Posts.category),
        ).where(Posts.id == post_id)
        result = await db.execute(stmt)
        orm_post = result.scalar_one_or_none()
        if orm_post is None:
            raise PostException("不存在当前查找的帖子")

        orm_post.is_top = is_top
        await db.commit()
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
        orm_post = await self.crud_get_post_details_by_id(db,post_id,user.uid,is_superuser=user.is_superuser)
        if orm_post is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="帖子不存在"
                )

        if orm_post.author_uid != user.uid and not user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="无权限删除此帖子")

        # ## 为什么要手动删图片（2026-09-21）
        # images 表和帖子之间是【多态软关联】（target_type + target_id，没有外键），
        # 所以数据库不会级联 —— 不删的话，图片记录和磁盘文件会变成孤儿：
        # 帖子里再也查不到它，但它一直占着磁盘和表行。
        # 这个调用只做操作不 commit，下面统一的 commit 会把"删图 + 删帖"放进同一事务。
        await ImageService.delete_images_by_target(db, "post", str(post_id))

        await db.delete(orm_post)
        await db.commit()
        return True
