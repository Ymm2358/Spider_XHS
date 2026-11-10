"""路径与本地配置。所有可调项集中在这里，不散落到业务代码。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "xhs.db"
REPORT_DIR = ROOT / "reports"
DRAFT_DIR = ROOT / "drafts"
CONFIG_DIR = ROOT / "config"

_ENV_LOADED = False


def load_env() -> None:
    global _ENV_LOADED
    if not _ENV_LOADED:
        load_dotenv(ROOT / ".env", override=False)
        _ENV_LOADED = True


def pc_cookie() -> str:
    load_env()
    cookie = (os.getenv("XHS_PC_COOKIE") or "").strip()
    if not cookie:
        raise RuntimeError(
            f"缺少 XHS_PC_COOKIE。把完整 Cookie 写进 {ROOT / '.env'} 的 XHS_PC_COOKIE="
        )
    missing = [name for name in ("a1=", "web_session=") if name not in cookie]
    if missing:
        raise RuntimeError(
            "Cookie 不完整，缺少 " + "、".join(missing) + "。"
            "请在已登录的浏览器里复制完整 Cookie 请求头，而不是 document.cookie。"
        )
    return cookie


def creator_cookie() -> str:
    load_env()
    cookie = (os.getenv("XHS_CREATOR_COOKIE") or "").strip()
    if not cookie:
        raise RuntimeError(
            f"缺少 XHS_CREATOR_COOKIE。发布相关功能需要单独配置，见 {ROOT / '.env'}"
        )
    return cookie


def proxies() -> Optional[dict]:
    load_env()
    url = (os.getenv("XHS_PROXY") or "").strip()
    if not url:
        return None
    return {"http": url, "https": url}


def ensure_dirs() -> None:
    for path in (DATA_DIR, RAW_DIR, REPORT_DIR, DRAFT_DIR, CONFIG_DIR):
        path.mkdir(parents=True, exist_ok=True)
