"""新增图片表

Revision ID: abcfdeda1df4
Revises: 0af95caa2ddc
Create Date: 2026-07-06 21:24:16.253327

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abcfdeda1df4'
down_revision: Union[str, Sequence[str], None] = '0af95caa2ddc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('images',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='图片id'),
    sa.Column('filename', sa.String(length=255), nullable=False, comment='磁盘文件名（UUID格式）'),
    sa.Column('target_type', sa.String(length=10), nullable=False, comment='关联类型：post / goods'),
    sa.Column('target_id', sa.String(length=36), nullable=False, comment='关联的帖子id或商品gid'),
    sa.Column('author_uid', sa.String(length=36), nullable=False, comment='上传者id'),
    sa.Column('sort_order', sa.Integer(), nullable=False, comment='排序'),
    sa.Column('created_time', sa.DateTime(), nullable=False, comment='创建时间'),
    sa.ForeignKeyConstraint(['author_uid'], ['user.uid'], onupdate='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('filename')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('images')
