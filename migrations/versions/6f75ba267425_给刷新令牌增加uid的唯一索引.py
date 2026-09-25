"""给刷新令牌增加 uid 的唯一索引，并补齐模型里已有、库中缺失的索引/约束

Revision ID: 6f75ba267425
Revises: d1e2f3a4b5c6
Create Date: 2026-09-25 20:57:25.529851

## 为什么把 autogenerate 的产物裁掉了一大半（2026-09-25）
autogenerate 生成的是「模型与数据库的**全部**差异」，不是「你这次想要的那一个改动」。
它原本生成了 17 条操作，其中只有最后一条是目标，其余全是历史积累的漂移。
直接跑会在 goods.classify 上炸：

    (3780) Referencing column 'classify' and referenced column 'id'
           in foreign key constraint 'fk_goods_classify' are incompatible.

因为 autogenerate 只改引用方 goods.classify → INTEGER，而被引用方
goods_classify.id 还是 varchar(36) —— MySQL 要求外键两端类型**严格一致**。
正确顺序应是 drop FK → 改被引用列 → 改引用列 → 重建 FK，那是独立的一件事。

本次只保留三类**安全**操作：
  ① 补索引：模型里有、库里没有（comments 复合索引、goods.update_time）
  ② 补唯一约束：模型里有、库里没有，且已实测现有数据无重复（messages / notifications）
  ③ 本次目标：token.user_uid 唯一约束

**明确排除**（各自单独立案，别再混进来）：
  - goods.classify / goods_classify.id 的 varchar(36) → Integer：
    实测数据是 '1'~'5' 的纯数字串、可转，但必须按
    drop FK → 改被引用列 → 改引用列 → 建 FK 的顺序做
  - 十几条 alter_column 的 comment 变更：纯注释，没有功能收益
  - drop_index('filename', 'images')：那是 images.filename 在库里本来就有唯一索引、
    模型漏写 unique=True 造成的漂移。正确修法是**补模型**，
    删掉库里的索引是功能回归（已同步改 models/model_image.py）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f75ba267425'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(conn, table: str, index: str) -> bool:
    """查 information_schema 判断某个索引是否已存在"""
    return bool(conn.execute(sa.text(
        "SELECT COUNT(*) FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = :t AND INDEX_NAME = :i"
    ), {"t": table, "i": index}).scalar())


def _create_index_if_missing(conn, index: str, table: str, columns: list) -> None:
    """幂等建索引：已存在就跳过

    ## 为什么不能直接 op.create_index
    `ix_comments_post_parent_time` 在本地**已经存在**了 ——
    上一轮 upgrade 的失败点在它后面，而 MySQL 的 DDL **不是事务性的**
    （alembic 日志里那句 "Will assume non-transactional DDL" 说的就是这个），
    失败点**之前**的语句会永久生效、不会回滚：
    索引建好了，alembic_version 却没推进。

    那为什么不"先删掉再让迁移重建"？因为这个索引的首列 post_id 正被外键
    `comments_ibfk_4` 征用（MySQL 允许外键复用复合索引的最左前缀），
    `DROP INDEX` 会报 1553 "needed in a foreign key constraint"，
    要删就得"删外键 → 删索引 → 重建外键"，代价和风险都大得多。

    所以做成幂等：本地有就跳过，服务器（没有这个索引）照常创建。
    """
    if not _index_exists(conn, table, index):
        op.create_index(index, table, columns, unique=False)


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # ---------- ① 模型有、库里没有的索引 ----------
    _create_index_if_missing(
        conn, 'ix_comments_post_parent_time', 'comments',
        ['post_id', 'parent_id', 'created_time'],
    )
    _create_index_if_missing(conn, 'ix_goods_update_time', 'goods', ['update_time'])

    # ---------- ② 模型有、库里没有的唯一约束 ----------
    # 加之前已实测 messages / notifications 无重复组合，不会因脏数据失败
    op.create_unique_constraint(
        'uq_message_conversation', 'messages', ['conversation_id', 'created_time'],
    )
    op.create_unique_constraint(
        'uq_notification_recipient_post', 'notifications',
        ['recipient_uid', 'post_id', 'created_time'],
    )

    # ---------- ③ 本次目标：一个 uid 只能有一行刷新令牌 ----------
    # ## 为什么必须是数据库约束而不是"应用层先查再写"
    # 原来 routers/user.py 的登录是 check-then-act：先查该 uid 有没有 token 行 → 没有就 add。
    # 两个并发请求会读到**同一个未提交快照**（InnoDB 默认 REPEATABLE READ，普通 SELECT
    # 是快照读、不加锁）→ 都判定为 None → 都 add → 出现两行，
    # 之后 crud_get_token_by_user_uid 的 scalar_one_or_none() 抛 MultipleResultsFound
    # → 被兜成 500 → **该用户登录/刷新/登出全部 500**，永久故障直到手工删行。
    # 让数据库保证"一个 uid 一行"比让应用层自己检查可靠 —— 应用层检查永远有这个窗口。
    #
    # ⚠️ 唯一约束只保证"不出错"。要让并发登录**都成功**（而不是第二个请求报 400），
    #    还得把 check-then-act 换成 MySQL 的 INSERT ... ON DUPLICATE KEY UPDATE。
    op.create_unique_constraint('uq_token_user_uid', 'token', ['user_uid'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_token_user_uid', 'token', type_='unique')
    op.drop_constraint('uq_notification_recipient_post', 'notifications', type_='unique')
    op.drop_constraint('uq_message_conversation', 'messages', type_='unique')
    conn = op.get_bind()
    if _index_exists(conn, 'goods', 'ix_goods_update_time'):
        op.drop_index('ix_goods_update_time', table_name='goods')

    # ⚠️ 这里【刻意不删】ix_comments_post_parent_time：
    # 它的首列 post_id 被外键 comments_ibfk_4 征用，DROP INDEX 会报
    # 1553 "needed in a foreign key constraint"。
    # 要删必须先删外键、删索引、再重建外键 —— 为一个"模型早就该有、
    # 只是历史上漏了迁移"的索引付这个代价不值得。
    # 留着它不影响正确性（模型里本来就定义了这个索引），
    # 所以这个 downgrade 是"不完全对称"的，属于知情的取舍。
