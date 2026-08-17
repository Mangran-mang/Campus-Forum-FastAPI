"""新增用户等级/经验系统与等级定义表

Revision ID: c1d2e3f4a5b6
Revises: abcfdeda1df4
Create Date: 2026-07-15 18:23:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'abcfdeda1df4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 用户表新增经验值、等级字段
    op.add_column('user', sa.Column('experience', sa.Integer(), nullable=False, server_default=sa.text('0'), comment='经验值'))
    op.add_column('user', sa.Column('level', sa.Integer(), nullable=False, server_default=sa.text('0'), comment='等级(0=新手,1~10)'))

    # 等级定义表（配置表，固定 10 级）
    op.create_table('level_config',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键'),
        sa.Column('level', sa.Integer(), nullable=False, comment='等级'),
        sa.Column('name', sa.String(length=50), nullable=False, comment='等级名称'),
        sa.Column('min_experience', sa.Integer(), nullable=False, comment='升级到该等级所需的最小经验值'),
        sa.Column('created_time', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('level')
    )

    # 初始化 10 级数据：100 / 500 / 1000 / 2000 / 3000 / 5000 / 10000 / 15000 / 20000 / 50000
    bind = op.get_bind()
    bind.execute(text("""
        INSERT INTO level_config (level, name, min_experience, created_time) VALUES
        (1,  '校园魔丸',     100,   NOW()),
        (2,  '超级魔丸',     500,   NOW()),
        (3,  '积极分子', 1000,  NOW()),
        (4,  '活跃用户', 2000,  NOW()),
        (5,  '资深用户', 3000,  NOW()),
        (6,  '达人',     5000,  NOW()),
        (7,  '专家',     10000, NOW()),
        (8,  '大佬',     15000, NOW()),
        (9,  '宗师',     20000, NOW()),
        (10, '校园的传说',     50000, NOW())
    """))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    bind.execute(text("DELETE FROM level_config"))
    op.drop_table('level_config')
    op.drop_column('user', 'level')
    op.drop_column('user', 'experience')
