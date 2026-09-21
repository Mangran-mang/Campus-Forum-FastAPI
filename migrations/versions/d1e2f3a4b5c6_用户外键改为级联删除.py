"""用户外键改为级联删除：让"删用户"能真正删掉

Revision ID: d1e2f3a4b5c6
Revises: a1b2c3d4e5f6
Create Date: 2026-09-21 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 要改的 5 条外键：(表名, 约束名, 是否保留 onupdate="CASCADE")
# 约束名是当初建表时 MySQL 自动生成的（模型里没写 name），
# 所以这里必须按【数据库里已有的名字】删，重建时也沿用同一个名字。
_FKS = [
    ("posts", "posts_ibfk_1", True),
    ("comments", "comments_ibfk_1", True),
    ("goods_comment", "goods_comment_ibfk_1", True),
    ("images", "images_ibfk_1", False),
    ("goods", "fk_goods_author_uid", False),
]


def upgrade() -> None:
    """Upgrade schema.

    为什么必须 drop 再 create：
    MySQL 不支持修改已有外键的 ON DELETE 行为，只能删掉重建。

    为什么要做这件事：
    这 5 条外键原本没有写 ondelete，MySQL 就按默认的 NO ACTION 处理 ——
    结果是"只要用户在这些表里有一行数据，DELETE 用户就会被拒绝"，
    接口层表现为 500（IntegrityError）。
    实测：发过一个帖 / 评论过一次 / 上传过一张图 / 发布过一个商品，
    以上任意一种情况都会让用户删不掉，等于"用过的用户都删不掉"。

    ⚠️ 本迁移带来的行为变化（是方案 A 的既定代价，不是 bug）：
      删用户 → 他的帖子被删（posts 这条 CASCADE）
             → 帖子下的评论也被删（comments.post_id 那条本来就是 CASCADE）
             → 【包括别人在他帖子下的评论】
      即"删一个用户"会顺带抹掉其他人对该用户内容的发言。
    """
    for table, cname, with_onupdate in _FKS:
        op.drop_constraint(cname, table, type_="foreignkey")
        op.create_foreign_key(
            cname,
            table,
            "user",
            ["author_uid"],
            ["uid"],
            ondelete="CASCADE",
            onupdate="CASCADE" if with_onupdate else None,
        )


def downgrade() -> None:
    """Downgrade schema.

    恢复成原来的行为（不写 ondelete → MySQL 默认 NO ACTION → 有数据的用户删不掉）。

    注意：降级【不会】把已经被级联删掉的数据找回来，
    降级只是把"删除时的行为"改回去。
    """
    for table, cname, with_onupdate in _FKS:
        op.drop_constraint(cname, table, type_="foreignkey")
        op.create_foreign_key(
            cname,
            table,
            "user",
            ["author_uid"],
            ["uid"],
            onupdate="CASCADE" if with_onupdate else None,
        )
