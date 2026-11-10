"""xhsops：小红书选题雷达的业务层。

上游 Spider_XHS 放在 vendor/spider_xhs/，保持原样不修改。
这里把 vendor 加进 sys.path，业务代码仍然可以 `import apis` / `import xhs_utils`，
升级上游时只替换 vendor 目录，不用改任何 import。
"""

from __future__ import annotations

import sys
from pathlib import Path

__version__ = "0.1.0"

_VENDOR = Path(__file__).resolve().parents[1] / "vendor" / "spider_xhs"
if _VENDOR.exists() and str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))
