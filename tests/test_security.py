"""tools/security.py 的单元测试

## 为什么先测这个文件
security 是认证的根：密码哈希、token 签发/解码、refresh 哈希，全在这里。
它一旦改坏，整个登录链路都挂，而且**坏的方式通常很隐蔽**
（比如哈希后面偷偷换了算法、同输入产出不同输出）——正是单元测试的用武之地。

## 这些测试都不碰数据库、不起服务
纯函数进、纯函数出，全部跑完在毫秒级。这是单元测试该有的样子：
快 → 你才会愿意每次都跑。
"""
import time
from datetime import timedelta

import jwt
import pytest

from config.config import Config
from tools import security


# ============ 密码哈希 ============

class TestPasswordHash:
    def test_hash_is_not_plaintext(self):
        """哈希结果绝不能等于明文 —— 最基础的一条底线"""
        raw = "my_password_123"
        assert security.get_password_hash(raw) != raw

    def test_hash_is_verifiable(self):
        """自己能验证自己：哈希后能验证通过"""
        raw = "my_password_123"
        hashed = security.get_password_hash(raw)
        assert security.verify_password(raw, hashed) is True

    def test_wrong_password_rejected(self):
        """错误密码必须验不过 —— 防止 verify 写成恒 True"""
        hashed = security.get_password_hash("correct_password")
        assert security.verify_password("wrong_password", hashed) is False

    def test_same_password_different_hash(self):
        """同一密码两次哈希结果不同（bcrypt 自动加盐）

        ## 为什么这条重要
        如果哪天有人把 bcrypt 换成 sha256（快哈希、无盐），这条会立刻挂 ——
        那时相同密码会产生相同哈希，撞库攻击就能一次性破解所有用同一密码的用户。
        这条断言就是在守护"必须加盐"这个性质。
        """
        raw = "same_password"
        h1 = security.get_password_hash(raw)
        h2 = security.get_password_hash(raw)
        assert h1 != h2
        # 但两个哈希都能验证同一个密码
        assert security.verify_password(raw, h1)
        assert security.verify_password(raw, h2)


# ============ token 签发 / 解码 ============

class TestCreateAccessToken:
    def test_payload_contains_required_keys(self):
        """载荷必须含 user / exp / jti / refresh 四个键"""
        token = security.create_access_token({"email": "a@b.com", "user_uid": "u1"})
        data = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        assert set(data.keys()) >= {"user", "exp", "jti", "refresh"}
        assert data["user"] == {"email": "a@b.com", "user_uid": "u1"}

    def test_refresh_flag_defaults_false(self):
        """默认签发的是访问令牌（refresh=False）"""
        token = security.create_access_token({"email": "a@b.com", "user_uid": "u1"})
        data = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        assert data["refresh"] is False

    def test_refresh_flag_can_be_true(self):
        """refresh=True 时载荷里的 refresh 必须是 True（区分两种令牌的依据）"""
        token = security.create_access_token(
            {"email": "a@b.com", "user_uid": "u1"}, refresh=True)
        data = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        assert data["refresh"] is True

    def test_jti_is_unique_per_call(self):
        """每次签发的 jti 必须不同

        ## 为什么这条重要
        jti 是"这一把令牌"的唯一身份证，登出拉黑黑名单靠它。
        如果两次签发 jti 相同 → 拉黑一把会误伤另一把（或者拉黑无效）。
        """
        payload = {"email": "a@b.com", "user_uid": "u1"}
        jtis = {jwt.decode(security.create_access_token(payload),
                           Config.JWT_SECRET,
                           algorithms=[Config.JWT_ALGORITHM])["jti"]
                for _ in range(20)}
        assert len(jtis) == 20


class TestDecodeToken:
    def test_roundtrip(self):
        """签发 → 解码，载荷应当能原样拿回来"""
        payload = {"email": "round@trip.com", "user_uid": "u9"}
        token = security.create_access_token(payload)
        data = security.decode_token(token)
        assert data is not None
        assert data["user"] == payload

    def test_garbage_returns_none(self):
        """垃圾字符串解码失败 → 返回 None（而不是抛异常）"""
        assert security.decode_token("this.is.not.a.jwt") is None

    def test_empty_string_returns_none(self):
        """空字符串也要返回 None 而不是崩溃"""
        assert security.decode_token("") is None

    def test_tampered_signature_returns_none(self):
        """篡改签名的 token 必须解不开

        ## 为什么这条重要
        这是 JWT 的**核心安全保证**：攻击者改了载荷内容但没法用密钥重新签名，
        所以服务端一验签名就知道被动过手脚。
        """
        token = security.create_access_token({"email": "a@b.com", "user_uid": "u1"})
        head, payload, _sig = token.split(".")
        tampered = f"{head}.{payload}.{'x' * 20}"
        assert security.decode_token(tampered) is None

    def test_wrong_secret_returns_none(self):
        """用别的密钥签发的 token 必须解不开（防止密钥配错还能通）

        ⚠️ 伪造密钥要 ≥32 字节：pyjwt 对短于 32 字节的 HS256 密钥会发
        InsecureKeyLengthWarning（RFC 7518 建议值）。测试里也别用短密钥，
        否则每次跑都刷一条 warning，久了就没人看 warning 了。
        """
        forged = jwt.encode(
            {"user": {"email": "evil@x.com", "user_uid": "evil"},
             "exp": int(time.time()) + 3600, "jti": "fake", "refresh": False},
            "a_completely_different_secret_that_is_long_enough_32bytes",
            algorithm=Config.JWT_ALGORITHM,
        )
        assert security.decode_token(forged) is None

    def test_expired_returns_none(self):
        """过期 token 必须解不开

        ⚠️ 注意这里用的是负数 expiry（-1 秒），即"1 秒前就过期了"。
        这比传 timedelta(seconds=0) 更可靠：0 秒的边界情况下
        pyjwt 可能因为毫秒级误差判定"还没过期"，让测试变得不稳定（flaky）。
        """
        token = security.create_access_token(
            {"email": "a@b.com", "user_uid": "u1"},
            expiry=timedelta(seconds=-1),
        )
        assert security.decode_token(token) is None


# ============ refresh token 哈希 ============

class TestHashToken:
    def test_deterministic(self):
        """同一输入必须产出同一哈希 —— 这是"验证靠再哈希比对"能成立的前提

        refresh 校验的第三步就是"把收到的 token 再哈希一次，跟库里那份比"。
        如果哈希不确定（比如掺了随机盐），比对永远失败。
        """
        token = "some.refresh.token"
        assert security.hash_token(token) == security.hash_token(token)

    def test_is_sha256_hex(self):
        """输出是 64 位十六进制（sha256 的固定长度）"""
        h = security.hash_token("abc")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_input_different_hash(self):
        """不同 token 哈希不同（否则任意 token 都能通过比对）"""
        assert security.hash_token("token_a") != security.hash_token("token_b")

    def test_known_value(self):
        """对已知输入断言固定输出 —— 防止实现被悄悄换掉

        ## 为什么用一条"已知答案"的断言
        上面几条都是"性质测试"（相同/不同/长度），它们无法发现
        "算法从 sha256 换成了 md5"这类改动（md5 也一样确定、也一样不同）。
        加一条对具体值的断言，就能锁死算法本身。

        值来源：sha256("abc")，可用 `echo -n abc | sha256sum` 独立复核。
        """
        assert security.hash_token("abc") == (
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        )
