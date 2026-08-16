"""商品表添加author_uid外键关联用户

Revision ID: b1c2d3e4f5a6
Revises: 5e892e7a9720
Create Date: 2026-07-06 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid



# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = '5e892e7a9720'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 先建 goods_classify（被外键引用的表必须先存在）
    op.create_table(
        'goods_classify',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(30), nullable=False, unique=True),
        sa.Column('created_time', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # 2. 再建 goods（两个外键分别指向 goods_classify.id 和 user.uid）
    op.create_table(
        'goods',
        sa.Column('gid', sa.String(36), primary_key=True, nullable=False),
        sa.Column('name', sa.String(30), nullable=False),
        sa.Column('classify', sa.Integer(), nullable=False),
        sa.Column('author_uid', sa.String(36), nullable=False, comment='发布者用户ID'),
        sa.Column('status', sa.Enum('在售', '已售出'), nullable=False),
        sa.Column('price', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('created_time', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('update_time', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # 3. 加外键约束
    op.create_foreign_key('fk_goods_classify', 'goods', 'goods_classify', ['classify'], ['id'])
    op.create_foreign_key('fk_goods_author_uid', 'goods', 'user', ['author_uid'], ['uid'])


def downgrade() -> None:
    op.drop_table('goods')
    op.drop_table('goods_classify')
