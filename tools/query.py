"""
通用查询条件构造工具

## 为什么单独开一个文件
"LIKE 模糊搜索"是这个项目里会用很多次的能力（帖子搜索、以后可能还有商品/用户搜索）。
它有三件必须做、但很容易忘的事：转义元字符、加两侧通配符、处理空关键词。
把这三件事收进一个函数，比在每个 crud 方法里重复写 + 写注释提醒自己可靠 ——
注释会被忽略，函数不会。
"""
from typing import Optional

from sqlalchemy import Column, UnaryExpression


def escape_like(keyword: str) -> str:
    """
    转义 LIKE 的元字符，让用户输入被当作【字面量】而非通配符

    python中“\\”代表\

    LIKE 的三个元字符：
        %   匹配任意多个字符（含 0 个）
        _   匹配任意单个字符
        \\  转义符本身
    后果举例：用户输入单个 "%" → 拼成 LIKE '%%%' → 匹配【所有】帖子。
    输入 "_" 更隐蔽：搜 "a_b" 会匹配到 "aab"/"axb"/"a1b"，用户完全看不懂。

    ## 为什么反斜杠必须第一个替换
    若先替换 % → 得到 '\\%'（人工加进去的转义符）；
    此时若再替换 \\ → 变成 '\\\\%'，转义符被转义两次，语义就变了。
    顺序（反斜杠 → % → _）不可调换。

    ## 参数
    keyword: 原始关键词（通常是用户输入）

    ## 返回
    可直接拼进 LIKE 模式的字符串（还没加两侧的 %）
    """
    return (
        keyword
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def like_contains(column: Column, keyword: Optional[str]) -> Optional[UnaryExpression]:
    """
    构造"column 包含 keyword（按字面量）"的 ORM 条件

    ## comment
    把"必须做但容易忘"的三步收在一处，调用方只管传字段和关键词：
      ① strip 两端空白（用户粘贴内容常带多余空格）
      ② escape_like 转义元字符
      ③ 两侧补 % 做包含匹配，并用 escape="\\\\" 显式声明转义符

    ## 为什么返回值可能是 None
    关键词为空时返回 None，让调用方【跳过】这个条件。
    这是刻意的：若这里返回 column.like("%%")，它会匹配所有行 ——
    一旦调用方判断失误（例如用 `if keyword is not None:` 而非 `if keyword:`），
    空关键词就会静默变成"搜出全表"，且不报错、极难排查。
    返回 None 把"要不要加这个条件"的决定明确交回调用方。

    ## 为什么显式写 escape="\\\\"
    MySQL 默认转义符本来就是 \\，所以不写通常也能工作。显式写的好处：
      ① PostgreSQL / SQLite 行为不同，写了就跨库通用
      ② 若有人开启 NO_BACKSLASH_ESCAPES 模式，不会静默失效
      ③ 读代码的人一眼知道你在这里做转义

    ## 参数
    column:  要匹配的列，如 Posts.title
    keyword: 用户输入的关键词，可为 None / 空串

    ## 返回
    ORM 过滤条件；关键词无效时返回 None
    """
    if not keyword or not keyword.strip():
        return None

    escaped = escape_like(keyword.strip())
    return column.like(f"%{escaped}%", escape="\\")
