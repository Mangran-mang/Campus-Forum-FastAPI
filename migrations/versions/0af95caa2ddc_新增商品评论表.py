"""新增商品评论表

Revision ID: 0af95caa2ddc
Revises: b1c2d3e4f5a6
Create Date: 2026-07-06 16:16:52.153927

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0af95caa2ddc'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('goods_comment',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='评论id'),
    sa.Column('content', sa.String(length=255), nullable=False, comment='评论内容'),
    sa.Column('goods_gid', sa.String(length=36), nullable=False, comment='商品id'),
    sa.Column('author_uid', sa.String(length=36), nullable=False, comment='作者id'),
    sa.Column('parent_id', sa.Integer(), nullable=True, comment='父评论id（支持楼中楼）'),
    sa.Column('created_time', sa.DateTime(), nullable=False, comment='创建时间'),
    sa.ForeignKeyConstraint(['author_uid'], ['user.uid'], onupdate='CASCADE'),
    sa.ForeignKeyConstraint(['goods_gid'], ['goods.gid'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['parent_id'], ['goods_comment.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('goods_comment')
