"""新增商品预定表 + notifications 加 goods_id

Revision ID: c7e2a91d4f60
Revises: b9c4e21f7a83
Create Date: 2026-10-12

## 为什么做这一条
商品交易模块要加"预定购买"（**不接支付** —— 平台只做撮合 + 沟通，把纠纷面压到最小）：
1. `goods_reservations`：记录买家对商品的购买意向（pending 预定中 / completed 已成交 / cancelled 已取消）。
   预定是**有状态的业务动作**，不是聊天的副作用 —— 有表才能显示"N 人预定"、卖家看"谁想买"、
   买家看"我预定了什么"，以及给"通知只发一次"提供可靠判据。
2. `notifications.goods_id`：让"有人想买你的商品"这条通知能定位到具体商品。
   不复用 `post_id` —— 同一列两种语义，将来查不出来。

## 为什么幂等（先查 information_schema 再动手）
MySQL 的 DDL **不在事务里**：中途失败时前面的语句已生效、版本号却没动，
所以"重跑同一条迁移"是必然会发生的事。建表前查 TABLES、加列前查 COLUMNS，
保证本地/线上重复执行都安全。

## 关键设计点（表结构层面）
- **唯一约束 `(gid, buyer_uid)` 是整张表的支点**：防重复预定 + 接口天然幂等 +
  "通知只发一次"的判据（插入成功 = 首次）。check-then-act 在并发下会漏，约束不会。
- `seller_uid` 冗余自 goods：`gid → seller` 关系永不变（商品不能换主人），
  冗余安全，换来卖家列表查询少一次 join。
- 外键 `gid` 指向 `goods.gid`，类型 **String(36)**（不是自增整数）——
  本项目主键有三种形态（user.uid / posts.id / goods.gid）。
- ⚠️ **外键两端"一致"不只是类型和长度，还包括字符集与排序规则**（2026-10-12 实测踩到）：
  本项目所有表是 `utf8mb4 / utf8mb4_unicode_ci`；如果建表时只写 `mysql_charset="utf8mb4"`
  而不指定 collation，MySQL 8 会给 **默认的 `utf8mb4_0900_ai_ci`** —— 与
  `utf8mb4_unicode_ci` 不兼容，建外键直接报
  `3780 Referencing column ... are incompatible`。
  所以这里必须显式 `mysql_collate="utf8mb4_unicode_ci"`，与既有表对齐。

## 代价（有意识接受）
- 多一张表 + 三条索引；当前量级（校园论坛）无感。
- notifications 多一列 + 一条索引：notifications 是高频写表，每次 INSERT 多维护
  一棵索引树 —— 可接受（这个索引支撑"按商品查通知"，将来要用）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e2a91d4f60'
down_revision: Union[str, Sequence[str], None] = 'b9c4e21f7a83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    # 每次都重新 inspect：DDL 之后 inspector 的结构缓存是旧的
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(table)}


def _foreign_keys(table: str) -> set[str]:
    return {fk["name"] for fk in sa.inspect(op.get_bind()).get_foreign_keys(table)}


def upgrade() -> None:
    # ---------- 1) goods_reservations 表 ----------
    if not _has_table("goods_reservations"):
        op.create_table(
            "goods_reservations",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="预定id"),
            sa.Column("gid", sa.String(36), nullable=False, comment="商品id"),
            sa.Column("buyer_uid", sa.String(36), nullable=False, comment="买家uid"),
            sa.Column("seller_uid", sa.String(36), nullable=False, comment="卖家uid（自商品冗余）"),
            sa.Column(
                "status", sa.String(20), nullable=False, server_default="pending",
                comment="预定状态: pending 预定中 / completed 已成交 / cancelled 已取消",
            ),
            sa.Column("created_time", sa.DateTime(), nullable=False, comment="预定时间"),
            sa.Column("updated_time", sa.DateTime(), nullable=False, comment="状态变更时间"),
            sa.PrimaryKeyConstraint("id", name="pk_goods_reservations"),
            sa.ForeignKeyConstraint(["gid"], ["goods.gid"], name="fk_reservation_gid", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["buyer_uid"], ["user.uid"], name="fk_reservation_buyer", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["seller_uid"], ["user.uid"], name="fk_reservation_seller", ondelete="CASCADE"),
            sa.UniqueConstraint("gid", "buyer_uid", name="uq_reservation_goods_buyer"),
            mysql_charset="utf8mb4",
            # 必须与既有表（utf8mb4_unicode_ci）一致，否则外键报 3780
            mysql_collate="utf8mb4_unicode_ci",
        )
        # 三条索引对应三种真实查询形状（见模型里的注释）
        op.create_index("idx_reservation_gid_status", "goods_reservations", ["gid", "status"])
        op.create_index("idx_reservation_seller_status", "goods_reservations", ["seller_uid", "status"])
        op.create_index("idx_reservation_buyer_time", "goods_reservations", ["buyer_uid", "created_time"])

    # ---------- 2) notifications.goods_id ----------
    if "goods_id" not in _columns("notifications"):
        op.add_column(
            "notifications",
            sa.Column("goods_id", sa.String(36), nullable=True, comment="相关商品id"),
        )
    if "fk_notification_goods" not in _foreign_keys("notifications"):
        op.create_foreign_key(
            "fk_notification_goods", "notifications", "goods",
            ["goods_id"], ["gid"], ondelete="CASCADE",
        )
    if "ix_notifications_goods_id" not in _indexes("notifications"):
        op.create_index("ix_notifications_goods_id", "notifications", ["goods_id"])


def downgrade() -> None:
    if "ix_notifications_goods_id" in _indexes("notifications"):
        op.drop_index("ix_notifications_goods_id", table_name="notifications")
    if "fk_notification_goods" in _foreign_keys("notifications"):
        op.drop_constraint("fk_notification_goods", "notifications", type_="foreignkey")
    if "goods_id" in _columns("notifications"):
        op.drop_column("notifications", "goods_id")

    if _has_table("goods_reservations"):
        op.drop_table("goods_reservations")
