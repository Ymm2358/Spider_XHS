"""扫码登录，把新 Cookie 写回 .env。

长期维护 Cookie 的正确方式不是手工复制，而是失效时重新扫一次码。
"""

from __future__ import annotations

from pathlib import Path

from .config import ROOT


def qr_login() -> str:
    """终端扫码登录，返回完整的 Cookie 请求头字符串。"""
    from xhs_utils.xhs_pc import XHSPcAuth

    auth = XHSPcAuth.from_qrcode_login(show_in_terminal=True)
    try:
        cookies = auth.cookies_for_url(auth.origin("api"))
        return "; ".join(f"{name}={value}" for name, value in cookies.items())
    finally:
        auth.close()


def save_cookie(cookie: str, path: Path | None = None) -> Path:
    """只替换 .env 里的 XHS_PC_COOKIE 行，保留其他配置。"""
    path = path or (ROOT / ".env")
    line = f"XHS_PC_COOKIE={cookie}"
    if not path.exists():
        path.write_text(line + "\n", encoding="utf-8")
        return path

    lines = path.read_text(encoding="utf-8").splitlines()
    replaced = False
    for index, current in enumerate(lines):
        if current.startswith("XHS_PC_COOKIE="):
            lines[index] = line
            replaced = True
            break
    if not replaced:
        lines.append(line)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
