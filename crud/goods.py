from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status
from sqlalchemy.sql.functions import func

from models.model_goods import Goods
from models.model_goods_classify import GoodsClassify
from models.model_goods_reservation import GoodsReservation
from models.model_user import User
from schemas.goods import GoodsCreatePyModel, GoodsUpdatePyModel

MAX_ACTIVE_GOODS = 10  # 每个用户最多同时上架 10 个商品


class GoodsService:
    async def get_all_goods(self, db: AsyncSession):
        stmt = select(Goods).options(
            selectinload(Goods.classify_rel),
            selectinload(Goods.author),# 遗留问题4
        ).order_by(Goods.update_time.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_goods(self, db:AsyncSession,gid:str):
        stmt = select(Goods).options(
            selectinload(Goods.classify_rel),
            selectinload(Goods.author),
        ).where(Goods.gid == gid)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_goods(
            self, db: AsyncSession, goods: GoodsCreatePyModel, author_uid: str
            ):# 遗留问题8,用len查数量问题
        # 限制每个用户的在售商品数量
        active_count_stmt = select(func.count()).where(
            Goods.author_uid == author_uid,
            Goods.status == "在售",
        )
        active_result = await db.execute(active_count_stmt)
        active_count = active_result.scalar_one()
        if active_count >= MAX_ACTIVE_GOODS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"已有 {active_count} 个在售商品，每人最多上架 {MAX_ACTIVE_GOODS} 个，请先下架部分商品后再发布",
            )

        # 检查商品分类是否存在
        classify_result = await db.execute(select(GoodsClassify).where(GoodsClassify.name == goods.classify))
        classify_obj = classify_result.scalar_one_or_none()
        if not classify_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="商品分类不存在", )

        goods_data = goods.model_dump()
        goods_data.pop('classify', None)  # 把前端传的字符串扔掉
        goods_data['classify'] = classify_obj.id  # 换成真正的 ID

        orm_goods = Goods(**goods_data, author_uid=author_uid)
        db.add(orm_goods)
        await db.commit()
        await db.refresh(orm_goods, ["classify_rel", "author"])
        return orm_goods

    async def update_goods(self, db:AsyncSession, gid:str, goods:GoodsUpdatePyModel, user: User):
        orm_goods = await self.get_goods(db, gid)
        if not orm_goods:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在",
            )
        # 只有商品作者或超级管理员才能修改
        if orm_goods.author_uid != user.uid and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限修改此商品",
            )
        update_data = goods.model_dump(exclude_unset=True)

        # 如果传了分类名称，转换为分类ID
        if 'classify' in update_data:
            classify_result = await db.execute(
                select(GoodsClassify).where(GoodsClassify.name == update_data['classify'])
            )
            classify_obj = classify_result.scalar_one_or_none()
            if not classify_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="商品分类不存在",
                )
            update_data['classify'] = classify_obj.id

        for field, value in update_data.items():
            setattr(orm_goods, field, value)
        await db.commit()
        await db.refresh(orm_goods, ["classify_rel", "author"])
        return orm_goods

    async def _get_reservation(
            self, db: AsyncSession, gid: str, buyer_uid: str
    ) -> GoodsReservation | None:
        """查某个买家对某个商品的预定记录（唯一约束保证最多一条）"""
        stmt = select(GoodsReservation).where(
            GoodsReservation.gid == gid,
            GoodsReservation.buyer_uid == buyer_uid,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def reserve_goods(
            self, db: AsyncSession, gid: str, buyer_uid: str
    ) -> tuple[GoodsReservation, int, bool]:
        """
        预定商品：写预定记录（幂等）→ 首次时通知卖家 → 建/取会话

        返回 (预定记录, 会话id, 是否之前已预定过)

        ## 为什么先查商品做业务校验，而不是直接插入靠外键兜底
        要给用户看得懂的原因（商品不存在 / 不能买自己的 / 已售出）；
        外键只会抛出一句看不懂的完整性错误。

        ## 幂等的两层（这个接口的核心）
        1. 先查一次 —— 快路径，绝大多数重复点击在这里就返回了；
        2. 唯一约束 uq_reservation_goods_buyer 兜底并发 —— 两个请求同时查不到时，
           只有一个能插入成功，另一个捕获 IntegrityError 后回滚重查。
           **正确性由约束保证，check 只是优化**（同 refresh_token 那条约定）。

        ## 通知为什么只发一次
        "插入成功" 就是"首次"这个事实的判据 —— notification 表自己没有业务唯一键，
        所以去重只能挂在这里，挂它身上挂不住。
        """

        # 先拿商品看是否存在,然后判断商品的作者是不是当前用户,然后判断商品是否在售
        goods = await self.get_goods(db, gid)
        if not goods:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
        if goods.author_uid == buyer_uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="不能预定自己发布的商品")
        if goods.status != "在售":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"商品当前为「{goods.status}」，无法预定",
            )

        # 上层校验通过后到这，说明商品存在且可以预定
        # 拿到购买者对商品的预定记录,判断他是不是第一次购买
        # ## 为什么用 inserted，而不是一路复用"是否首次"
        # inserted 只表示"这次确实是我插进去的"，且**只会从 False 变 True（单向）**；
        # 而"是否首次"这个判断会在 except 分支里被改写成 False —— 一旦复用，
        # 正确性就依赖"块内某处改过它"这个细节，读代码的人必须做时序推理，改动时极易静默出错。
        # 单向变量没有这个问题：置 True 只有一条路径（commit 成功）。
        inserted = False
        reservation = await self._get_reservation(db, gid, buyer_uid)

        # 如果不是第一次购买，插入预定记录
        if reservation is None:
            reservation = GoodsReservation(
                gid=gid,
                buyer_uid=buyer_uid,
                seller_uid=goods.author_uid,  # 冗余自商品：gid→seller 永不变
            )
            db.add(reservation)
            try:
                await db.commit()
                await db.refresh(reservation)
                inserted = True
            except IntegrityError:
                # 并发下另一个请求刚插成功 → 回滚后按"已预定"处理，而不是把 500 抛给用户
                await db.rollback()
                reservation = await self._get_reservation(db, gid, buyer_uid)

            # 只有"这次确实是我插的"才通知卖家；并发抢输的那个请求不发。
            # 通知去重靠的就是这里 + 唯一约束 —— notification 表自身没有业务唯一键。
            if inserted:
                # 方法内导入 service：避免 crud 模块之间的循环引用（项目里 UserService 也这么处理）
                from crud.notification import NotificationService

                await NotificationService().crud_add_notification(db, {
                    "recipient_uid": goods.author_uid,
                    "sender_uid": buyer_uid,
                    "notif_type": "goods_reserve",
                    "goods_id": gid,
                    "post_id": None,
                    "content": f"有人想买你的商品《{goods.name}》",
                })

        # 会话无论是否首次都要拿：买家点这个按钮的真实目的就是进去聊
        from crud.message import MessageService

        conv = await MessageService().crud_get_or_create_conversation(
            db, buyer_uid, goods.author_uid)

        return reservation, conv.id, not inserted

    async def delete_goods(self, db:AsyncSession, gid:str, user: User):
        orm_goods = await self.get_goods(db, gid)
        if not orm_goods:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在",
            )
        # 只有商品作者或超级管理员才能删除
        if orm_goods.author_uid != user.uid and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限删除此商品",
            )
        await db.delete(orm_goods)
        await db.commit()