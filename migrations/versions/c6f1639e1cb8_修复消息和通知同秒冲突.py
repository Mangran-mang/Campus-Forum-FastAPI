"""修复消息和通知的唯一约束（同秒冲突）

Revision ID: c6f1639e1cb8
Revises: 6f75ba267425
Create Date: 2026-09-26 11:28:32.212090

## 为什么把 autogenerate 的产物裁掉一大半（2026-09-26）
autogenerate 生成了 19 条操作，其中**只有 4 条是本次目标**，
其余 15 条全是历史积累的漂移（`goods.classify` 改类型 + 十几条 comment 变更），
直接跑会在 `goods.classify` 上炸：

    (3780) Referencing column 'classify' and referenced column 'id'
           in foreign key constraint 'fk_goods_classify' are incompatible.

那个漂移已在本迁移之后单独用一个迁移修掉（`goods_classify` 类型修正），
修掉之后 autogenerate 就不会再生成它了。

## ⚠️ 顺序必须"先建新索引、再删旧索引"
`uq_message_conversation` 的首列 `conversation_id` 正被外键
`messages_ibfk_1`（conversation_id → conversations.id）**征用** ——
MySQL 允许外键复用复合索引的最左前缀。
此时直接 `DROP INDEX` 会报：

    1553  Cannot drop index '...': needed in a foreign key constraint

**先建好新索引**（首列同样是 `conversation_id`），外键的支撑角色就交接过去了，
旧索引才能删掉。
（autogenerate 生成的是"先 drop 后 create"，顺序反了 —— 这里手工调过来。）

## 为什么 notifications 的索引列用 is_read 而不是 post_id
`crud/notification.py::crud_get_user_notifications` 的查询形状是：
    WHERE recipient_uid = ?  [AND is_read = false]   ORDER BY created_time DESC
`post_id` 从来不出现在这个查询的过滤条件里（它在原唯一约束里的作用是"同一用户
对同一帖子的通知去重"，改索引后已无意义）；
真正被用到的是过滤列 `is_read` 和排序列 `created_time`。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6f1639e1cb8'
down_revision: Union[str, Sequence[str], None] = '6f75ba267425'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ---------- messages：(conversation_id, created_time) 唯一约束 → 普通索引 ----------
    # 先建后删，否则撞 1553（外键 messages_ibfk_1 占着这个索引的最左前缀）
    op.create_index(
        'idx_message_conversation', 'messages',
        ['conversation_id', 'created_time'], unique=False,
    )
    op.drop_index('uq_message_conversation', table_name='messages')

    # ---------- notifications：(recipient_uid, post_id, created_time) 唯一约束 → 普通索引 ----------
    # 同样先建后删（外键 notifications_ibfk_2 占着 recipient_uid 的最左前缀）
    op.create_index(
        'idx_notification_recipient_post', 'notifications',
        ['recipient_uid', 'is_read', 'created_time'], unique=False,
    )
    op.drop_index('uq_notification_recipient_post', table_name='notifications')


def downgrade() -> None:
    """Downgrade schema."""
    # 反向同样"先建后删"，才能保证任一时刻都有索引在支撑外键
    op.create_index(
        'uq_notification_recipient_post', 'notifications',
        ['recipient_uid', 'post_id', 'created_time'], unique=True,
    )
    op.drop_index('idx_notification_recipient_post', table_name='notifications')

    op.create_index(
        'uq_message_conversation', 'messages',
        ['conversation_id', 'created_time'], unique=True,
    )
    op.drop_index('idx_message_conversation', table_name='messages')
