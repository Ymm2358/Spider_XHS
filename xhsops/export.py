"""把 HTML 渲染成 PDF / PNG。

用本机 Chromium 内核浏览器（Edge / Chrome / 夸克）的无头模式，不装额外浏览器。
优先顺序：环境变量 XHSOPS_BROWSER > Edge > Chrome > 夸克。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

CANDIDATES = [
    os.getenv("XHSOPS_BROWSER", ""),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Quark\quark.exe"),
    os.path.expandvars(r"%APPDATA%\Quark\quark.exe"),
]

FLAGS = [
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--disable-background-networking",
    "--hide-scrollbars",
    "--virtual-time-budget=3000",
]


class RenderError(RuntimeError):
    pass


def find_browser() -> str:
    for path in CANDIDATES:
        if path and Path(path).exists():
            return path
    raise RenderError(
        "找不到可用的 Chromium 浏览器。装 Edge/Chrome，或设置环境变量 XHSOPS_BROWSER 指向浏览器 exe。"
    )


def _file_url(path: Path) -> str:
    return path.resolve().as_uri()


def _run(browser: str, args: list[str], timeout: int = 120) -> None:
    profile = tempfile.mkdtemp(prefix="xhsops-render-")
    try:
        command = [browser, *FLAGS, f"--user-data-dir={profile}", *args]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if result.returncode != 0:
            tail = (result.stderr or result.stdout or "").strip()[-500:]
            raise RenderError(f"浏览器渲染失败（{result.returncode}）：{tail}")
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def to_pdf(html_path: Path, pdf_path: Path, browser: str | None = None) -> Path:
    browser = browser or find_browser()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        pdf_path.unlink()
    _run(
        browser,
        [
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            _file_url(html_path),
        ],
    )
    if not pdf_path.exists():
        raise RenderError("PDF 没有生成，检查浏览器是否支持无头打印")
    return pdf_path


def to_png(html_path: Path, png_path: Path, width: int = 1080, height: int = 1440, browser: str | None = None) -> Path:
    browser = browser or find_browser()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    if png_path.exists():
        png_path.unlink()
    _run(
        browser,
        [
            f"--window-size={width},{height}",
            f"--screenshot={png_path}",
            _file_url(html_path),
        ],
    )
    if not png_path.exists():
        raise RenderError("PNG 没有生成，检查浏览器是否支持无头截图")
    return png_path
