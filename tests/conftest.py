"""pytest 全局配置

## comment
放这里的 fixture 会被所有测试文件共享（不需要 import）。

## 为什么把项目根加进 sys.path
pytest 默认把「tests 所在目录」加进 sys.path，但不会加项目根。
所以 `tests/test_xxx.py` 里写 `from tools.query import ...` 会 ImportError。
这里显式插入项目根，让测试可以像路由代码一样用绝对 import。

（另一种做法是在项目根放 pyproject.toml / pytest.ini 并配 pythonpath，
但那个配置需要 pytest>=7 且要额外装插件支持；显式改 sys.path 最直白、零依赖。）
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
