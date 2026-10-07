from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from models import User, Posts, Goods, Comments, Like


class AdminService:
    async def get_users_information(
        self, db: AsyncSession, page: int = 1, page_size: int = 15
    ):
        """
        获取所有用户低粒度信息，如发帖数、发评论数、发商品数等信息
        """

        # 稳定限制页码和页大小
        page = max(page, 1)
        page_size = min(max(page_size, 1), 20)

        post_count = (
            select(func.count(Posts.id))
            .where(Posts.author_uid == User.uid)
            .correlate(User)  # 显式说明到外层查询User里去找要用的列
            .scalar_subquery()
        )

        comment_count = (
            select(func.count(Comments.id))
            .where(Comments.author_uid == User.uid)
            .correlate(User)
            .scalar_subquery()
        )

        goods_count = (
            select(func.count(Goods.gid))
            .where(Goods.author_uid == User.uid)
            .correlate(User)
            .scalar_subquery()
        )

        user_count = await db.execute(select(func.count()).select_from(User))
        total_user = user_count.scalar_one()

        stmt = (
            select(
                User,
                post_count.label("post_count"),
                comment_count.label("comment_count"),
                goods_count.label("goods_count"),
            )
            .order_by(User.created_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await db.execute(stmt)).all()  # 每行 = (User, int, int, int)
        return rows, total_user, page, page_size

    async def get_posts_information(
        self, db: AsyncSession, page: int = 1, page_size: int = 15
    ):
        """
        返回帖子类型、浏览量、评论数、点赞数、是否公开
        """
        # 稳定限制页码和页大小
        page = max(page, 1)
        page_size = min(max(page_size, 1), 20)

        comment_count = (
            select(func.count(Comments.id))
            .where(Comments.post_id == Posts.id)
            .correlate(Posts)
            .scalar_subquery()
        )

        like_count = (
            select(func.count(Like.id))
            .where(Like.post_id == Posts.id)
            .correlate(Posts)
            .scalar_subquery()
        )

        total = await db.execute(select(func.count()).select_from(Posts))
        total_posts = total.scalar_one()

        stmt = (
            select(
                Posts,
                comment_count.label("comment_count"),
                like_count.label("like_count"),
            )
            .options(joinedload(Posts.author), joinedload(Posts.category))
            .order_by(Posts.created_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        rows = (await db.execute(stmt)).all()
        return rows, total_posts, page, page_size

    async def get_goods_information(
        self, db: AsyncSession, page: int = 1, page_size: int = 15
    ):
        """
         重点讲解
        获取所有商品低粒度信息，包括商品的种类、价格、在售情况等信息
        """
        # 稳定限制页码和页大小
        page = max(page, 1)
        page_size = min(max(page_size, 1), 20)

        total = await db.execute(select(func.count()).select_from(Goods))
        total_goods = total.scalar_one()

        stmt = (
            select(Goods)
            .options(joinedload(Goods.author), joinedload(Goods.classify_rel))
            .order_by(Goods.created_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await db.execute(stmt)).all()
        return rows, total_goods, page, page_size

    # crud/admin.py
    from datetime import date

    async def get_overview(self, db: AsyncSession):
        today = date.today()  # 本地日期，与 created_time 存储基准一致

        # ## 为什么每个 count 都要 select_from
        # SELECT 列表里只有聚合函数、没有列对象，SQLAlchemy 推不出 FROM 哪张表，
        # 必须显式 select_from —— 和你现有 total 的写法同一条规则
        def total(model):
            return select(func.count()).select_from(model).scalar_subquery()

        def today_new(model):
            return (
                select(func.count())
                .select_from(model)
                .where(model.created_time >= today)  # 裸范围条件 → 走刚建的索引
                .scalar_subquery()
            )

        stmt = select(
            total(User).label("user_total"),
            today_new(User).label("user_today"),
            total(Posts).label("post_total"),
            today_new(Posts).label("post_today"),
            total(Goods).label("goods_total"),
            today_new(Goods).label("goods_today"),
        )
        row = (await db.execute(stmt)).one()
        return dict(row._mapping)  # 8 个 int，一个 ORM 实体都不构造

    """async def get_trends(self, db: AsyncSession, days: int):
        start = date.today() - timedelta(days=days - 1)
        stmt = (
            select(
                func.date(Posts.created_time).label("date"),
                func.count(Posts.id).label("count"),
            )
            .where(Posts.created_time >= start)  # 裸范围条件 → 走刚建的索引
            .group_by(
                func.date(Posts.created_time)
            )  # 函数包裹在分组上，行集已被过滤缩小，无妨
        )
        rows = (await db.execute(stmt)).all()
        found = {str(r.date): r.count for r in rows}
        # ## 补零：缺的天填 0，前端拿到就能画，不用做日期对齐
        result = [
            {
                "date": (start + timedelta(days=i)).isoformat(),
                "count": found.get((start + timedelta(days=i)).isoformat(), 0),
            }
            for i in range(days)
        ]
        return result"""


