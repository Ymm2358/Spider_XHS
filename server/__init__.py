"""统一后端。

engine/ 来自 XHS_ALL_IN_ONE 的 backend/app，只改导入前缀；
local/ 是本项目自己的接口。

vendor/spider_xhs 在这里注入 sys.path，engine 里的
`from apis...` / `from xhs_utils...` 才能解析到我们维护的签名层。
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_VENDOR = _ROOT / "vendor" / "spider_xhs"
if _VENDOR.exists() and str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))
