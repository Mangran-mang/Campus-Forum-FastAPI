# 测试（pytest）

## 怎么跑

```bash
# 项目根目录，用项目自带的 venv
.venv/Scripts/python.exe -m pytest          # 跑全部（约 3 秒）
.venv/Scripts/python.exe -m pytest -q       # 安静模式，只看结果
.venv/Scripts/python.exe -m pytest tests/test_query.py          # 单个文件
.venv/Scripts/python.exe -m pytest -k escape                    # 只跑名字含 escape 的
.venv/Scripts/python.exe -m pytest -x                           # 第一个失败就停
```

## 测试分层

| 文件 | 测什么 | 碰数据库？ |
|---|---|---|
| `test_security.py` | 密码哈希、JWT 签发/解码、refresh 哈希 | ❌ |
| `test_query.py` | 搜索转义、条件拼装 | ❌ |
| `test_exceptions.py` | 重复键分流、响应信封 | ❌ |

**目前 50 条全部是纯单元测试** —— 不碰数据库、不起服务、不用清理现场，2.65 秒跑完。
这是刻意的：**只有跑得快，你才会每次都跑。**

## 为什么不测接口（以及如果要测该怎么做）

⚠️ 本项目**不能**用 `fastapi.testclient.TestClient` 打真实接口。
原因见项目 `MEMORY.md`：aiomysql 的全局连接池在 ASGI 测试下会复用事件循环，
导致**同一 TestClient 连续请求随机 500**，排查时极具误导性。

要测接口，必须**起真 uvicorn**：

```python
import subprocess

@pytest.fixture(scope="session")
def server():
    """起一个真实服务，整个测试会话共用，结束后关掉"""
    proc = subprocess.Popen(
        [".venv/Scripts/python.exe", "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8011"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    # 等端口就绪（轮询 /docs）
    ...
    yield "http://127.0.0.1:8011"
    proc.terminate()
    proc.wait(timeout=10)
```

**（可选，尚未实现）** 如果以后要做接口测试：
1. 新建 `tests/test_api_search.py`
2. 照上面写 `server` fixture
3. 记得用 `pytest.mark.integration` 标记，并用时间戳造唯一测试账号、跑完清理

## 写测试的约定

- **函数名用 `test_` 开头，用 `assert` 表达期望**（不要 `assertEqual`，那是 unittest 的风格）
- **每个测试只验证一件事** —— 名字要能当"这条测试在防什么"读
- **测试里的注释写"为什么要测这条"**，而不是"这行在干什么"。
  断言本身已经说明了在测什么，注释的价值在于记录**当初踩过的坑**
- **用 `pytest.mark.parametrize` 处理"同一逻辑、多组输入"**（见 `test_empty_keyword_returns_none`）
- **发现 bug 时先写一条会挂的测试，再修** —— 这样修完能证明"真的修好了"，
  而且以后不会再退化（回归保护）
