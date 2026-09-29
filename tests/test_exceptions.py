"""tools/exceptions.py 异常分流逻辑的单元测试

## 为什么这个文件值得测
`_duplicate_key_message` 的 bug **不会让接口报错** —— 它只会悄悄返回**错误的提示文案**。

2026-09-25 那次的真实 bug 就是这样：原实现
    if "username_UNIQUE" in error_msg or "Duplicate entry" in error_msg:
        → "用户名已存在"
那个 `or` 把**任何表**的重复键都吞成"用户名已存在"（而 `username_UNIQUE`
这个索引在当前库里根本不存在，所以 100% 走错文案）。
用户重复注册邮箱、重复点赞、重复收藏，全被告知"用户名已存在"。

这种 bug **用眼睛看不出来**（代码逻辑读起来"好像没问题"），
用接口测试也很难覆盖全（要构造 10 种冲突场景）。
但用单元测试，喂几个真实的 MySQL 报错字符串就能把全部 17 条 hints 钉死。
"""
import pytest

from tools.exceptions import (
    _duplicate_key_message,
    error_response,
    success_response,
    HTTP_STATUS_MESSAGE,
)


# ============ _duplicate_key_message：按索引名分流 ============

class TestDuplicateKeyMessage:
    """用**真实的 MySQL 报错格式**做输入

    ⚠️ 格式来源（实测）：
      MySQL 8.0: Duplicate entry 'x' for key 'categories.name'   ← 表名.索引名
      MySQL 5.7: Duplicate entry 'x' for key 'name'              ← 只有索引名
    两种都要能命中，因为 hints 表里既列了 "user.email" 也列了 "email"。
    """

    @pytest.mark.parametrize("error_msg,expected_fragment", [
        # MySQL 8.0 格式（带表名）
        ("(1062, \"Duplicate entry 'a@b.com' for key 'user.email'\")", "邮箱"),
        ("(1062, \"Duplicate entry 'tom' for key 'user.username'\")", "用户名"),
        ("(1062, \"Duplicate entry '5' for key 'categories.name'\")", "板块名称"),
        ("(1062, \"Duplicate entry 'x' for key 'token.uq_token_user_uid'\")", "登录状态冲突"),
        # MySQL 5.7 格式（无表名）—— 只有 hints 表里单独列过的才命中
        ("(1062, \"Duplicate entry 'a@b.com' for key 'email'\")", "邮箱"),
        ("(1062, \"Duplicate entry 'tom' for key 'username'\")", "用户名"),
    ])
    def test_by_index_name(self, error_msg, expected_fragment):
        """报错里的索引名能决定文案"""
        msg = _duplicate_key_message(error_msg)
        assert expected_fragment in msg, f"输入 {error_msg!r} 得到 {msg!r}"

    def test_mysql57_bare_index_name_falls_back(self):
        """⚠️ 记录一个**已知覆盖盲区**（2026-09-29 由 pytest 发现）

        MySQL 8.0 报 `for key 'categories.name'`（带表名）→ 命中 "categories" hint ✅
        MySQL 5.7 报 `for key 'name'`（只有索引名）→ `"categories" in "name"` 为假
        → 掉到通用兜底"数据冲突，请检查提交的内容"。

        本项目跑的是 MySQL 8.0，所以**线上不会触发**。
        但这条断言把这个事实固定下来：
          - 如果哪天删掉 "categories" hint 而测试还挂着 → 说明 8.0 路径也坏了
          - 如果哪天升级/降级 MySQL 版本导致行为变化 → 这条会提醒你重新评估
        ⚠️ 不要为了"让它命中 5.7"而把 "name" 加进 hints —— "name" 太泛，
           会误伤其它表里叫 name 的索引，属于得不偿失。
        """
        msg = _duplicate_key_message(
            "(1062, \"Duplicate entry '5' for key 'name'\")")
        assert msg == "数据冲突，请检查提交的内容"

    def test_message_never_leaks_internals(self):
        """⚠️ 文案里绝不能出现表名 / 索引名 / 原始 SQL

        这些是内部结构（表名、约束名、字段名），泄露给前端是安全隐患。
        这条测试守住"只返回人话"这个约定。
        """
        msg = _duplicate_key_message(
            "(1062, \"Duplicate entry 'x' for key 'user.email'\")")
        for leaked in ["Duplicate entry", "for key", "user.email", "1062", "mysql"]:
            assert leaked not in msg, f"文案泄露了内部信息 {leaked!r}: {msg!r}"

    def test_unparsable_falls_back_to_generic(self):
        """解析不出索引名时回落通用文案（宁可笼统，也不吐原始报错）"""
        msg = _duplicate_key_message("some totally unexpected database error")
        assert "Duplicate entry" not in msg
        assert len(msg) > 0

    def test_message_conversation_precedes_conversation(self):
        """⚠️ 这条守护 hints 表的**顺序**

        ## 为什么要专门测顺序
        `uq_message_conversation`（消息表）含子串 "conversation"，
        而会话表的 hint 就是 "conversation"。
        hints 表用 `if hint in key` 顺序匹配 —— 如果把 "conversation" 排在
        "uq_message_conversation" **前面**，消息表的冲突会被抢先判成"会话已存在"。

        实测踩过一次，所以钉一条测试。
        """
        msg = _duplicate_key_message(
            "(1062, \"Duplicate entry 'x' for key 'uq_message_conversation'\")")
        assert "会话已存在" not in msg, (
            f"消息表冲突被误判成会话冲突，hints 顺序错了：{msg!r}"
        )


# ============ 响应信封 ============

class TestResponseEnvelope:
    def test_success_shape(self):
        """成功响应必须是三层结构"""
        r = success_response(data={"a": 1}, message="ok")
        assert r == {"code": 200, "message": "ok", "data": {"a": 1}}

    def test_success_default_data_none(self):
        """不传 data 时是 None（如纯删除操作）"""
        r = success_response(message="删除成功")
        assert r["data"] is None and r["code"] == 200

    def test_error_message_fallback_by_status(self):
        """message 为空时按状态码兜底成中文，不吐空串"""
        r = error_response(404)
        assert r["message"] == HTTP_STATUS_MESSAGE[404]
        assert r["data"] is None

    def test_error_non_string_message_converted(self):
        """message 传了 dict 也必须转成字符串（保证前端拿到的一定是 str）"""
        r = error_response(400, {"错误": "详情"})
        assert isinstance(r["message"], str)

    def test_error_custom_message_kept(self):
        """有自定义 message 时原样保留（业务文案优先于兜底）"""
        r = error_response(403, "无权访问")
        assert r["message"] == "无权访问"
