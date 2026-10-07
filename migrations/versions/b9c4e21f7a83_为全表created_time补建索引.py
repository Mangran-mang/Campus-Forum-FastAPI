"""为全表 created_time 补建索引（对齐 model_base 的 index=True）

Revision ID: b9c4e21f7a83
Revises: d7a24f1e9c33
Create Date: 2026-10-07

## 为什么要做这一条
`models/model_base.py` 给 Base.created_time 加了 `index=True`，所有继承 Base 的
ORM 模型都声明了这个索引，但数据库一直没建（2026-10-07 实测 SHOW INDEX：
15 张业务表全部没有 ix_<表名>_created_time）—— 又一次"改模型 ≠ 改数据库"。
动机：后台趋势查询（每日新帖/新用户）是 `WHERE created_time >= X` 的范围过滤，
没索引就是全表扫；范围条件不套函数，正好能吃上这个索引（分组的 DATE() 不影响）。

## 为什么手写而不是 autogenerate
项目迁移有历史遗留问题，一直走手写路线；且 autogenerate 生成的是
"模型与库的全部差异"，还要人工裁剪 —— 直接手写更可控。

## 为什么幂等（先查 information_schema 再建）
MySQL 的 DDL **不在事务里**：15 条 CREATE INDEX 中途失败时，前面的已生效、
版本号没动 —— 重跑同一条迁移是必然发生的事，所以每张表先查
STATISTICS 再决定建不建，保证重跑安全（本地/线上都适用）。

## 代价（写清楚，是有意识接受而不是没看见）
- 空间：每张表多一棵 B+ 树（同学已确认接受）
- 写放大：token / likes / bookmarks / notifications 是高频写表，每次 INSERT
  多维护一棵索引树 —— 当前量级（校园论坛）毫秒级无感，真到了要优化的那天
  再单独 DROP 这几张表的索引即可（它们不按 created_time 查询）。

## 索引命名
`ix_<表名>_created_time` —— 与 SQLAlchemy 对 `index=True` 的默认命名
（ix_ + 列标签）一致：将来若真跑 autogenerate，模型与库对得上，
不会重复生成这批索引。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9c4e21f7a83'
down_revision: Union[str, Sequence[str], None] = 'd7a24f1e9c33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 2026-10-07 直连本地库 SHOW TABLES 的真实清单（排除 alembic_version），
# 15 张表全部实测有 created_time 列、全部没有该索引
TABLES = [
    'bookmarks', 'categories', 'comments', 'conversations', 'goods',
    'goods_classify', 'goods_comment', 'images', 'level_config', 'likes',
    'messages', 'notifications', 'posts', 'token', 'user',
]


def _index_exists(conn, table: str, index_name: str) -> bool:
    """查 information_schema 判断索引是否已存在（幂等的全部意义所在）"""
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = :table AND INDEX_NAME = :index_name"
        ),
        {"table": table, "index_name": index_name},
    )
    return result.scalar_one() > 0


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    for table in TABLES:
        index_name = f"ix_{table}_created_time"
        if not _index_exists(conn, table, index_name):
            op.create_index(index_name, table, ['created_time'])


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    for table in TABLES:
        index_name = f"ix_{table}_created_time"
        if _index_exists(conn, table, index_name):
            op.drop_index(index_name, table)
