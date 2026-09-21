"""用户外键改为级联删除：让"删用户"能真正删掉

Revision ID: d1e2f3a4b5c6
Revises: a1b2c3d4e5f6
Create Date: 2026-09-21 17:10:00.000000

"""
from typing import Optional, Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 要改的外键：(表名, 列名, 是否保留 onupdate="CASCADE")
TARGETS = [
    ("posts", "author_uid", True),
    ("comments", "author_uid", True),
    ("goods_comment", "author_uid", True),
    ("images", "author_uid", False),
    ("goods", "author_uid", False),
]


def _find_fk_name(bind, table: str, column: str) -> Optional[str]:
    """查这条外键在【当前这个数据库里】真实叫什么名字

    ## comment
    ### 为什么不能把约束名写死（2026-09-21 踩的坑）
    `posts_ibfk_1` 这类名字是 MySQL 建表时**自动生成**的，编号规则是
    "该表上第几个自动命名的外键"，而且 **drop 之后编号不会重用**。

    所以只要某张表曾经删过外键再重建（哪怕中间隔了很久），编号就会往后走：
        posts_ibfk_1  ->  posts_ibfk_2  ->  ...

    本地库和服务器库虽然是同一套迁移建出来的，但只要中间有人手动改过表结构、
    或建表顺序有差异，名字就对不上 —— 结果就是：
    迁移在本地跑通，到服务器报
        (1091, "Can't DROP 'posts_ibfk_1'; check that column/key exists")

    所以这里改成【运行时去 information_schema 查真实名字】，
    本地和服务器都能跑，以后谁再动过表结构也不怕。
    ### 用 DATABASE() 而不是写库名
    避免迁移文件硬编码到某个具体库名上（本地叫 mangran，换环境也不用改）。
    """
    row = bind.execute(
        sa.text(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :t
              AND COLUMN_NAME = :c
              AND REFERENCED_TABLE_NAME = 'user'
            LIMIT 1
            """
        ),
        {"t": table, "c": column},
    ).fetchone()
    return row[0] if row else None


def _rebuild(bind, table: str, column: str, with_onupdate: bool, ondelete) -> None:
    """把一条外键删掉、再按指定的 ondelete 重建

    ## comment
    ### 为什么必须 drop 再 create
    MySQL 不支持直接修改已有外键的 ON DELETE 行为，只能删掉重建。
    ### 重建时沿用查到的原名
    这样 schema 不会因为跑了一次迁移就多出一批"名字变了"的外键，方便日后人工核对。
    ### 查不到时的兜底
    万一表里根本没有这条外键（比如某次手工改表删掉了），就直接建一条，
    而不是让整个迁移失败 —— 这个迁移的目标是"最终状态是 CASCADE"，
    不是"必须删掉某个叫 X 的约束"。
    """
    name = _find_fk_name(bind, table, column)
    if name is None:
        op.create_foreign_key(
            "fk_%s_%s" % (table, column), table, "user", [column], ["uid"],
            ondelete=ondelete,
            onupdate="CASCADE" if with_onupdate else None,
        )
        return

    op.drop_constraint(name, table, type_="foreignkey")
    op.create_foreign_key(
        name, table, "user", [column], ["uid"],
        ondelete=ondelete,
        onupdate="CASCADE" if with_onupdate else None,
    )


def upgrade() -> None:
    """把 5 条指向 user.uid 的外键改成 ON DELETE CASCADE

    ## comment
    ### 为什么做这件事
    这 5 条外键原本没写 ondelete，MySQL 按默认的 NO ACTION 处理 ——
    结果是"只要用户在这些表里有一行数据，DELETE 用户就被拒绝"，接口层表现为 500。
    实测：发过一个帖 / 评论过一次 / 上传过一张图 / 发布过一个商品，
    以上任意一种都让用户删不掉，等于"用过的用户都删不掉"。

    ### ⚠️ 本迁移带来的行为变化（方案 A 的既定代价，不是 bug）
      删用户 -> 他的帖子被删（posts 这条 CASCADE）
             -> 帖子下的评论也被删（comments.post_id 那条本来就是 CASCADE）
             -> 【包括别人在他帖子下的评论】
      即"删一个用户"会顺带抹掉其他人在他内容下的发言。
    """
    bind = op.get_bind()
    for table, column, with_onupdate in TARGETS:
        _rebuild(bind, table, column, with_onupdate, "CASCADE")


def downgrade() -> None:
    """恢复成原来的行为（不写 ondelete -> MySQL 默认 NO ACTION -> 有数据的用户删不掉）

    ## comment
    注意：降级【不会】把已经被级联删掉的数据找回来，
    降级只是把"删除时的行为"改回去。
    """
    bind = op.get_bind()
    for table, column, with_onupdate in TARGETS:
        _rebuild(bind, table, column, with_onupdate, None)
