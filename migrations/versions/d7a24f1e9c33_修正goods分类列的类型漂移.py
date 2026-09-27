"""修正 goods.classify / goods_classify.id 的类型漂移（varchar(36) → Integer）

Revision ID: d7a24f1e9c33
Revises: c6f1639e1cb8
Create Date: 2026-09-26

## 为什么要单独做这一条
模型里这两列早就写成 `Integer` 了，而数据库一直是 `varchar(36)` —— 属于**历史漂移**。
后果：**每次 `alembic revision --autogenerate` 都会生成这一条**，
而它按表名字母序**只改引用方** `goods.classify`，被引用方 `goods_classify.id` 还是 varchar，
MySQL 要求外键两端类型**严格一致** → 每次都炸在同一个地方：

    (3780) Referencing column 'classify' and referenced column 'id'
           in foreign key constraint 'fk_goods_classify' are incompatible.

2026-09-25 和 09-26 连续两次踩在这里（两次都是"生成的迁移没裁剪就直接跑"）。
把漂移本身修掉，这个坑以后就不会再出现 —— 这是**治本**，裁剪只是治标。

## 为什么顺序是「drop FK → 改被引用列 → 改引用列 → 重建 FK」
MySQL 不允许外键两端类型不一致的中间状态，所以：
① 先摘掉外键，让两列可以各自独立改
② **先改被引用列** `goods_classify.id`
③ 再改引用列 `goods.classify`
④ 两端都是 INTEGER 了，重建外键
（反着来 —— 先改引用方 —— 就是 autogenerate 的做法，必然撞 3780。）

## 数据安全性（已实测，做这种迁移前必须先查数据）
```
goods_classify.id : '1' '2' '3' '4' '5'      ← 全是纯数字串
goods.classify    : '1' '2' '4'
```
转 INTEGER 不丢值、不报错。
⚠️ 若里面混了 UUID 之类非数字字符串，这一步会失败或截断 —— 所以**先 SELECT 看一眼**再动手。

## 重建外键时为什么没写 ondelete
原 DDL 是：
    CONSTRAINT `fk_goods_classify` FOREIGN KEY (`classify`) REFERENCES `goods_classify` (`id`)
**没有** ON DELETE / ON UPDATE 规则（即默认 RESTRICT），所以这里也不写、保持原样。
⚠️ 重建外键最容易翻车的地方就在这：**原规则必须原样抄回来**，
否则会悄悄把"删分类会被拒绝"变成"删分类连带删商品"。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = 'd7a24f1e9c33'
down_revision: Union[str, Sequence[str], None] = 'c6f1639e1cb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ① 摘掉外键，两列才能独立改类型
    op.drop_constraint('fk_goods_classify', 'goods', type_='foreignkey')

    # ② 先改【被引用列】（主键；加 autoincrement 与模型的 Integer 主键对齐）
    op.alter_column(
        'goods_classify', 'id',
        existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=36),
        type_=sa.Integer(),
        existing_nullable=False,
        autoincrement=True,
    )

    # ③ 再改【引用列】
    op.alter_column(
        'goods', 'classify',
        existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=36),
        type_=sa.Integer(),
        existing_nullable=False,
    )

    # ④ 两端都一致了，重建外键（原样：无级联规则）
    op.create_foreign_key(
        'fk_goods_classify', 'goods', 'goods_classify',
        ['classify'], ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_goods_classify', 'goods', type_='foreignkey')

    # 反向：先改引用列，再改被引用列
    op.alter_column(
        'goods', 'classify',
        existing_type=sa.Integer(),
        type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=36),
        existing_nullable=False,
    )
    op.alter_column(
        'goods_classify', 'id',
        existing_type=sa.Integer(),
        type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=36),
        existing_nullable=False,
        autoincrement=False,
    )

    op.create_foreign_key(
        'fk_goods_classify', 'goods', 'goods_classify',
        ['classify'], ['id'],
    )
