"""token表:refresh_token 改存 sha256 哈希,新增 jti 列

Revision ID: a1b2c3d4e5f6
Revises: 9f279cb462e2
Create Date: 2026-09-03 21:20:00.000000

"""
from typing import Sequence, Union

import hashlib

import jwt
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

from config.config import Config

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9f279cb462e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _to_hash(raw: str) -> str:
    """明文 refresh token 转单向 sha256 哈希（只用于落库比对，不回传）"""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def upgrade() -> None:
    """Upgrade schema.

    为什么在本迁移里直接解码存量 token：
    旧行躺的是明文 refresh token，若只加列不动数据，安全修复等于没做——
    数据库一旦泄露，攻击者拿到的仍是可直接使用的明文。
    此处把存量行原位替换为哈希，用户当前会话不中断：客户端仍持原始 token，
    刷新时服务端再哈希比对即可命中。
    """
    # 1) 先加可空列，回填完再收紧为 NOT NULL
    op.add_column('token', sa.Column(
        'jti', sa.String(length=64), nullable=True,
        comment='刷新令牌的jti,登出时用来拉黑',
    ))

    bind = op.get_bind()
    rows = bind.execute(text("SELECT id, refresh_token FROM token")).mappings().all()

    # 2) 存量行原位转哈希 + 回填 jti
    for row in rows:
        raw = row["refresh_token"]
        try:
            payload = jwt.decode(raw, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        except jwt.PyJWTError:
            # 解不出来的（过期/伪造/脏数据）直接清掉，反正签名过不了也刷不了
            bind.execute(
                text("DELETE FROM token WHERE id = :i"), {"i": row["id"]},
            )
            continue
        bind.execute(
            text("UPDATE token SET refresh_token = :h, jti = :j WHERE id = :i"),
            {"h": _to_hash(raw), "j": payload["jti"], "i": row["id"]},
        )

    # 3) 收紧非空约束
    op.alter_column('token', 'jti',
                    existing_type=sa.String(length=64),
                    nullable=False)


def downgrade() -> None:
    """Downgrade schema.

    注意：单向哈希无法还原成明文，降级后 refresh_token 列仍是哈希。
    若旧代码(按明文解码/比对)跑在降级后的库上，所有存量会话需重新登录。
    """
    op.drop_column('token', 'jti')
