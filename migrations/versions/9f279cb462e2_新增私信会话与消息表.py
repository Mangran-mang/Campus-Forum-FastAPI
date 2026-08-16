"""新增私信会话与消息表

Revision ID: 9f279cb462e2
Revises: b4d68482ce7a
Create Date: 2026-08-03 17:46:02.954838

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9f279cb462e2'
down_revision: Union[str, Sequence[str], None] = 'b4d68482ce7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增私信会话表与消息表"""
    op.create_table('conversations',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='会话id'),
    sa.Column('user_a_uid', sa.String(length=36), nullable=False, comment='参与者A(uid较小)'),
    sa.Column('user_b_uid', sa.String(length=36), nullable=False, comment='参与者B(uid较大)'),
    sa.Column('created_time', sa.DateTime(), nullable=False, comment='会话创建时间'),
    sa.Column('updated_time', sa.DateTime(), nullable=False, comment='最后消息时间'),
    sa.ForeignKeyConstraint(['user_a_uid'], ['user.uid'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_b_uid'], ['user.uid'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_a_uid', 'user_b_uid', name='uq_conversation_pair')
    )
    op.create_table('messages',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='消息id'),
    sa.Column('conversation_id', sa.Integer(), nullable=False, comment='所属会话id'),
    sa.Column('sender_uid', sa.String(length=36), nullable=False, comment='发送者uid'),
    sa.Column('content', sa.Text(), nullable=False, comment='消息内容'),
    sa.Column('created_time', sa.DateTime(), nullable=False, comment='发送时间'),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sender_uid'], ['user.uid'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """回退：删除私信表"""
    op.drop_table('messages')
    op.drop_table('conversations')
