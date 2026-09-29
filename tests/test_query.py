"""tools/query.py 的单元测试（就是刚加的搜索转义）

## 为什么这个文件特别值得测
`escape_like` 的正确性**不体现在"能不能跑通"上** —— 它有 bug 时：
  - 不报错
  - 不抛异常
  - 搜索结果看起来"有返回"
只是**结果悄悄变多或变少**（用户搜 "%" 得到全站帖子、搜 "a_b" 得到一堆无关帖）。
这种"静默错误"只能靠断言把"期望输出"写死来防。

## 这类"输入 → 输出纯映射"的函数，是单元测试性价比最高的目标
不需要数据库、不需要网络、不需要清理现场。写 30 行测试，永久守护这个逻辑。
"""
import pytest

from tools.query import escape_like


# ============ escape_like：元字符转义 ============

class TestEscapeLike:
    def test_plain_text_untouched(self):
        """普通文本原样返回（不能无脑到处加反斜杠）"""
        assert escape_like("python") == "python"
        assert escape_like("正常中文") == "正常中文"
        assert escape_like("hello world") == "hello world"

    def test_percent_escaped(self):
        """% 必须转义 —— 否则用户搜 "%" 会变成 LIKE '%%%'，匹配全表"""
        assert escape_like("%") == "\\%"
        assert escape_like("100%") == "100\\%"
        assert escape_like("50%off") == "50\\%off"

    def test_underscore_escaped(self):
        """_ 必须转义 —— 否则搜 "a_b" 会匹配到 "aab"/"axb"/"a1b" """
        assert escape_like("_") == "\\_"
        assert escape_like("a_b") == "a\\_b"

    def test_backslash_escaped(self):
        """反斜杠本身也要转义（它同时是转义符）"""
        assert escape_like("a\\b") == "a\\\\b"

    def test_backslash_must_be_replaced_first(self):
        """⚠️ 这条守护"替换顺序"这个最容易改错的地方

        ## 为什么必须反斜杠先替换
        输入 "%" 时：
          正确顺序：先 \\ → 无变化，再 % → "\\%"           ✓ 3 个字符
          错误顺序：先 %  → "\\%"（人工加的转义符），
                    再 \\ → "\\\\%"（把人工转义符又转了一次）✗ 4 个字符
        后者的语义变了：它会去匹配"一个字面反斜杠 + 任意字符"，
        用户搜 "%" 就搜不到本该匹配的帖子。

        ## 所以这条不是在测"结果好看"，是在测"顺序没被调换"
        如果哪天有人为了"可读性"把两个 replace 换位，这条会立刻挂。
        """
        result = escape_like("%")
        assert result == "\\%"
        assert len(result) == 2, "转义符被二次转义了（% 和 \\ 的替换顺序被调换）"

    def test_mixed_metacharacters(self):
        """混合场景：三种元字符同时出现"""
        assert escape_like("50%_test\\") == "50\\%\\_test\\\\"

    def test_empty_string(self):
        """空字符串安全返回空（不能崩）"""
        assert escape_like("") == ""

    def test_idempotent_on_plain_input(self):
        """无元字符时，转义多少次结果都一样（幂等）"""
        once = escape_like("abc")
        twice = escape_like(once)
        assert once == twice == "abc"

    def test_not_idempotent_on_metacharacters(self):
        """⚠️ 但含元字符时**不幂等** —— 这条是"警示性测试"

        ## 为什么要写一条"证明它不幂等"的测试
        因为"不小心转义两次"是很容易犯的错（比如 router 转一次、crud 又转一次）。
        这条测试把这个事实**明确记录下来**：
        转义必须只做一次，放在数据进入查询构造的入口处。

        如果哪天有人真在两层各转一次，这条测试不会挂（它只是描述现状），
        但上面 test_backslash_must_be_replaced_first 会挂 —— 两条配合起来，
        足以让人看出"多转了一层"。
        """
        once = escape_like("100%")          # "100\\%"
        twice = escape_like(once)           # "100\\\\%"
        assert once != twice
        assert twice == "100\\\\\\%"


# ============ like_contains：条件拼装 ============

class TestLikeContains:
    """like_contains 需要 SQLAlchemy 列对象，这里只测"空关键词返回 None"这个关键契约。

    ## 为什么只测这一条
    拼出来的 SQL 长什么样，属于"集成范畴"（要看编译结果）。
    而"空关键词返回 None"是**纯粹的调用契约**：调用方靠 `if cond is not None`
    来决定"要不要加这个条件"。如果这里退化成返回一个恒真条件，
    调用方的判断就失效了 —— 空搜索会静默变成"查全表"。

    这条契约是这个函数存在的主要理由（否则直接写 column.like 就行了），
    所以它最值得一条独立断言。
    """

    @pytest.mark.parametrize("empty", [None, "", "   ", "\t", "\n", "  \t \n "])
    def test_empty_keyword_returns_none(self, empty):
        """各种"空"的形态都必须返回 None（而不是空格、空串、恒真条件）"""
        from models.model_posts import Posts
        from tools.query import like_contains
        assert like_contains(Posts.title, empty) is None

    def test_non_empty_returns_condition(self):
        """非空关键词必须返回真条件（不能连正常路径也返回 None）"""
        from models.model_posts import Posts
        from tools.query import like_contains
        cond = like_contains(Posts.title, "python")
        assert cond is not None

    def test_generated_sql_uses_escape_clause(self):
        """生成的 SQL 必须带 ESCAPE 子句

        ## 为什么用字符串断言 SQL
        转义符写错（比如漏了 escape="\\\\"），在 MySQL 里因为默认转义符恰好是 \\
        而"看起来能工作"，但换库（PostgreSQL/SQLite 默认转义符不是 \\）就失效。
        而且若有人开启 NO_BACKSLASH_ESCAPES 模式，也会静默失效。
        断言 SQL 里带 ESCAPE，就把"必须显式声明"这件事钉死了。
        """
        from sqlalchemy import select
        from sqlalchemy.dialects import mysql

        from models.model_posts import Posts
        from tools.query import like_contains

        cond = like_contains(Posts.title, "a%b")
        stmt = select(Posts.id).where(cond)
        sql = str(stmt.compile(dialect=mysql.dialect()))
        assert "ESCAPE" in sql.upper(), f"生成的 SQL 缺少 ESCAPE 子句：{sql}"
