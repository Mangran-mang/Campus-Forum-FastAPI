"""
一次性脚本：造一个本地管理员账号（2026-10-05方案 A 的第0 步）

## 为什么必须先做这一步
本地库5 个用户 `is_superuser` **全是 0**（这也回答了待修清单的 C2）。
方案 A 的权限校验靠 `UserChecker(True)` →读 `user.is_superuser`，
没有管理员的话后台接口一律 403，根本测不起来。

而**不能走注册接口**：/api/user/add 里 crud_add_new_user 有
    orm_user.is_superuser = False   # 强制默认为非管理员
所以注册出来的必然是普通用户，必须事后手动改库提权。

## 幂等
已存在同名管理员时会跳过并直接报出uid，不会重复创建、不会覆盖密码。
"""
import asyncio
import sys
from urllib.parse import urlparse

import aiomysql

sys.path.insert(0, ".")

from config.config import Config  # noqa: E402
from tools.security import get_password_hash  # noqa: E402

ADMIN_EMAIL = "admin@local.dev"
ADMIN_PASSWORD = "AdminLocal123"
ADMIN_NICKNAME = "本地管理员"


async def main():
    u = urlparse(Config.DATABASE_URL.replace("mysql+aiomysql", "mysql"))
    conn = await aiomysql.connect(
        host=u.hostname, port=u.port,
        user=u.username, password=u.password, db=u.path.lstrip("/"),
    )
    async with conn.cursor() as cur:
        # ① 先看有没有
        await cur.execute("SELECT uid, is_superuser FROM user WHERE email=%s",
                          (ADMIN_EMAIL,))
        row = await cur.fetchone()
        if row:
            print(f"账号已存在 uid={row[0]} is_superuser={row[1]}")
            if not row[1]:
                # 存在但不是管理员 → 提权（幂等：重复跑只会把它设成1）
                await cur.execute("UPDATE user SET is_superuser=1 WHERE email=%s",
                                  (ADMIN_EMAIL,))
                await conn.commit()
                print("已提权为管理员")
            else:
                print("已是管理员，无需改动")
            await cur.execute("SELECT uid FROM user WHERE email=%s", (ADMIN_EMAIL,))
            print("uid =", (await cur.fetchone())[0])
            print(f"\n登录用：{ADMIN_EMAIL}  /  {ADMIN_PASSWORD}")
            conn.close()
            return

        # ② 没有就建
        await cur.execute(
            "INSERT INTO user "
            "(uid, email, password, username, nickname, gender, "
            " is_active, is_superuser, experience, level, created_time, updated_time) "
            "VALUES (UUID(), %s, %s, %s, %s, '未知', 1, 1, 0, 0, NOW(), NOW())",
            (ADMIN_EMAIL, get_password_hash(ADMIN_PASSWORD), ADMIN_NICKNAME,
             ADMIN_NICKNAME),
        )
        await conn.commit()
        print("已创建管理员账号")

        await cur.execute("SELECT uid, is_superuser, is_active FROM user WHERE email=%s",
                          (ADMIN_EMAIL,))
        r = await cur.fetchone()
        print(f"  uid={r[0]} superuser={r[1]} active={r[2]}")
        print(f"\n登录用：{ADMIN_EMAIL}  /  {ADMIN_PASSWORD}")

    conn.close()


asyncio.run(main())
