from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from models.model_base import Base


class GoodsReservation(Base):
    """
    商品预定记录：买家对某个商品表达的购买意向

    与 goods.status 的分工（两个正交维度，刻意不合并）
    goods.status      → 卖家视角：这个商品还卖不卖（在售 / 已售出）
    goods_reservation → 买家视角：我想不想买（预定中 / 已成交 / 已取消）

    预定是一个**有状态的业务动作**，不是聊天的副作用。有表才能：
    """
    __tablename__ = "goods_reservations"
    __table_args__ = (
        # ## 整张表的支点
        # 同一买家对同一商品只能有一条记录。重复点击由这个约束兜底，
        # 不靠"先查后插"（check-then-act 在并发下会漏）。
        # 它同时提供三件事：防重复预定 / 接口天然幂等 / "通知只发一次"的判据
        # （插入成功 = 首次，此时才发通知）。
        UniqueConstraint("gid", "buyer_uid", name="uq_reservation_goods_buyer"),
        # 商品详情页算"有效预定数"：WHERE gid = ? AND status = 'pending'
        Index("idx_reservation_gid_status", "gid", "status"),
        # 卖家看"谁想买我的东西"：WHERE seller_uid = ? AND status = ?
        Index("idx_reservation_seller_status", "seller_uid", "status"),
        # 买家看"我预定了什么"：WHERE buyer_uid = ? ORDER BY created_time DESC
        Index("idx_reservation_buyer_time", "buyer_uid", "created_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="预定id")
    gid: Mapped[str] = mapped_column(
        String(36), ForeignKey("goods.gid", ondelete="CASCADE"), nullable=False, comment="商品id"
    )
    buyer_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid", ondelete="CASCADE"), nullable=False, comment="买家uid"
    )
    # ## 为什么把卖家冗余一份
    # gid → seller 这条关系**永不变**（商品不能换主人），所以冗余是安全的；
    # 换来的是卖家列表查询（WHERE seller_uid = ?）不用 join 商品表。
    # 注意：这类冗余只在"源关系不可变"时才成立，可变字段的冗余要另行处理同步。
    seller_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid", ondelete="CASCADE"), nullable=False, comment="卖家uid（自商品冗余）"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="预定状态: pending 预定中 / completed 已成交 / cancelled 已取消",
    )
    created_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="预定时间")
    updated_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        # 刻意不用 onupdate：这个字段只在"状态流转"时该变，
        # 由业务代码显式赋值（同 model_posts.updated_time 的结论，见那边注释）
        comment="状态变更时间（业务代码手动赋值，不用 onupdate）",
    )
