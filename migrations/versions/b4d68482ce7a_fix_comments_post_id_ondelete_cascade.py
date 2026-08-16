"""fix_comments_post_id_ondelete_cascade

Revision ID: b4d68482ce7a
Revises: c1d2e3f4a5b6
Create Date: 2026-07-22 21:08:05.922285

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b4d68482ce7a'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """将 comments.post_id 外键从 onupdate=CASCADE 改为 ondelete=CASCADE"""
    op.drop_constraint(op.f('comments_ibfk_2'), 'comments', type_='foreignkey')
    op.create_foreign_key(None, 'comments', 'posts', ['post_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """回退：恢复 onupdate=CASCADE"""
    op.drop_constraint(None, 'comments', type_='foreignkey')
    op.create_foreign_key(op.f('comments_ibfk_2'), 'comments', 'posts', ['post_id'], ['id'], onupdate='CASCADE')
