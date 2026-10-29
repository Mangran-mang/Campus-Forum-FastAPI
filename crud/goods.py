from datetime import datetime

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
        """
        返回指定商品信息以及预定情况
        """
        # ## reserve_count 是"相关子查询"而不是 join 聚合
        # 详情页要显示"已有 N 人预定"（只算 pending）。用标量子查询：
        # 不会像 join + group by 那样复制行，也不需要额外的分组处理。
        # 只有详情走这条（get_all_goods 不算）—— 列表页不显示这个数字，
        # 没必要为每一行都多跑一次聚合。

        # 拿到指定商品的预定人数
        reserve_count_subq = (
            select(func.count())
            .select_from(GoodsReservation)
            .where(
                GoodsReservation.gid == Goods.gid,
                GoodsReservation.status == "pending",
            )
            .scalar_subquery()
        )

        # 拿到指定商品的信息和预定人数
        stmt = select(Goods, reserve_count_subq).options(
            selectinload(Goods.classify_rel),
            selectinload(Goods.author),
        ).where(Goods.gid == gid)
        row = (await db.execute(stmt)).first()
        if not row:
            return None
        orm_goods, reserve_count = row
        # 挂成非映射属性：GoodsDetailOut 靠它输出 reserve_count。
        # SQLAlchemy 不会把它当列（不是 mapped_column），只是普通 Python 属性。
        orm_goods.reserve_count = reserve_count or 0
        return orm_goods

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
        # ## 为什么用 should_notify 这一个标志，而不是"是否首次"一路复用
        # 需要通知卖家的情况有两种，且都不依赖任何会被改写的中间状态：
        #   ① 这次确实是我插进去的（commit 成功）
        #   ② 之前被取消过，这次"复活"成 pending
        # 标志只会从 False 变 True（单向），所以没有"块内被改写、后面还要重新判断"的时序陷阱。
        should_notify = False
        reservation = await self._get_reservation(db, gid, buyer_uid)

        # 如果没有预定记录，插入预定记录
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
                should_notify = True
            except IntegrityError:
                # 并发下另一个请求刚插成功 → 回滚后按"已预定"处理，而不是把 500 抛给用户
                await db.rollback()
                reservation = await self._get_reservation(db, gid, buyer_uid)
        elif reservation.status == "cancelled":
            # ## 复活：唯一约束 (gid, buyer_uid) 决定了"取消过就不能再插一条新的"
            # 只能把原来那条改回 pending。否则买家被取消一次之后就永远无法再预定这个商品
            # —— 会撞唯一约束，再被当成"已预定"，而且那条状态还是 cancelled，语义是错的。
            reservation.status = "pending"
            reservation.updated_time = datetime.now()  # 新表也不设 onupdate，状态流转手动记时间
            await db.commit()
            should_notify = True

        # 只有"这次真的产生了有效预定"才通知卖家；并发抢输的请求不发。
        # 通知去重靠的就是这里 + 唯一约束 —— notification 表自身没有业务唯一键。
        if should_notify:
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

        return reservation, conv.id, not should_notify

    async def get_reservations(
            self, db: AsyncSession, gid: str, user: User
    ) -> list[GoodsReservation]:
        """
        某个商品的预定列表（按预定时间倒序）

        ## 权限：只有商品作者或超级管理员
        "谁想买我的东西"是卖家侧的信息。如果谁拿到 gid 就能查，等于把买家的购买意向
        公开了 —— 这类"看起来只是列表"的接口最容易漏权限。
        """
        goods = await self.get_goods(db, gid)
        if not goods:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
        if goods.author_uid != user.uid and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="只能查看自己商品的预定")

        stmt = (
            select(GoodsReservation)
            # 列表要显示买家昵称 —— 必须预加载，否则序列化时触发异步懒加载 → MissingGreenlet 500
            .options(selectinload(GoodsReservation.buyer))
            .where(GoodsReservation.gid == gid)
            .order_by(GoodsReservation.created_time.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def complete_reservation(
            self, db: AsyncSession, rid: int, user: User
    ) -> GoodsReservation:
        """
        确认成交：预定 → completed；商品 → 已售出；其余 pending → cancelled（并通知他们）

        ## 为什么三件事必须在同一个事务里
        它们是同一个业务事实（"这个商品卖给了这个人"）的三个侧面。
        分三次提交，中途失败就会留下"商品已售出但预定额还挂着"这类不自洽的状态——
        而这类状态没有自愈机制，只能人工修数据。

        ## 为什么要通知没买到的买家
        他们在等消息。商品卖掉了却不告知，他们会一直以为自己还有机会
        （商品页虽然会显示"已售出"，但不是每个人都会回头再看一眼）。
        """
        # 一次查询把预定和商品都取出来：后面要校验权限（作者）并同时改两边
        stmt = (
            select(GoodsReservation, Goods, GoodsReservation.buyer)
            .join(Goods, Goods.gid == GoodsReservation.gid)
            .where(GoodsReservation.id == rid)
        )
        row = (await db.execute(stmt)).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预定记录不存在")
        reservation, goods, _buyer = row

        if goods.author_uid != user.uid and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="只有商品作者能确认成交")
        if reservation.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"该预定当前为「{reservation.status}」，无法确认成交",
            )

        now = datetime.now()
        reservation.status = "completed"
        reservation.updated_time = now
        goods.status = "已售出"

        # 其余还在等的人 —— 一起取消掉（他们没买到）
        others_stmt = select(GoodsReservation).where(
            GoodsReservation.gid == goods.gid,
            GoodsReservation.id != rid,
            GoodsReservation.status == "pending",
        )
        others = list((await db.execute(others_stmt)).scalars().all())
        for o in others:
            o.status = "cancelled"
            o.updated_time = now

        await db.commit()
        # commit 后对象已过期但 expire_on_commit=False，属性可直接读；
        # buyer 关系由上面那条查询的 selectinload 一并取回，序列化不会触发懒加载
        await db.refresh(reservation, ["buyer"])

        if others:
            # 批量通知（一次提交）—— 这里失败不该影响"成交"这个已提交的事实，
            # 所以放在 commit 之后：通知是附带的，成交才是主流程
            from crud.notification import NotificationService

            await NotificationService().crud_add_notifications(db, [
                {
                    "recipient_uid": o.buyer_uid,
                    "sender_uid": user.uid,
                    "notif_type": "goods_sold",
                    "goods_id": goods.gid,
                    "post_id": None,
                    "content": f"你预定的商品《{goods.name}》已被卖出",
                }
                for o in others
            ])

        return reservation

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