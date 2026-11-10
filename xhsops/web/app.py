"""本地桥接服务：接收浏览器插件送来的页面数据。

只监听 127.0.0.1，所有写接口都要 token。token 首次启动时生成，
写在 data/token.txt，插件弹窗里填一次即可。
"""

from __future__ import annotations

import json
import secrets
import time
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse

from ..config import DATA_DIR, ensure_dirs
from .. import store
from ..ingest import parse, save

TOKEN_PATH = DATA_DIR / "token.txt"
INBOX = DATA_DIR / "raw" / "extension"

app = FastAPI(title="xhs-ops bridge", docs_url=None, redoc_url=None)


def get_token() -> str:
    ensure_dirs()
    if not TOKEN_PATH.exists():
        TOKEN_PATH.write_text(secrets.token_urlsafe(24), encoding="utf-8")
    return TOKEN_PATH.read_text(encoding="utf-8").strip()


def _day_dir() -> Path:
    folder = INBOX / time.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "xhs-ops", "time": time.strftime("%Y-%m-%dT%H:%M:%S")}


@app.get("/stats")
def stats() -> dict:
    total = 0
    today = 0
    day = time.strftime("%Y-%m-%d")
    if INBOX.exists():
        for folder in INBOX.iterdir():
            if not folder.is_dir():
                continue
            count = len(list(folder.glob("*.json")))
            total += count
            if folder.name == day:
                today = count

    conn = store.connect()
    try:
        notes = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        comments = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
        ext_notes = conn.execute(
            "SELECT COUNT(*) FROM notes WHERE source LIKE 'ext:%'"
        ).fetchone()[0]
    finally:
        conn.close()

    return {
        "ok": True,
        "raw_today": today,
        "raw_total": total,
        "notes": notes,
        "ext_notes": ext_notes,
        "comments": comments,
        "day": day,
    }


@app.post("/ingest")
async def ingest(request: Request, x_xhsops_token: str = Header(default="")) -> dict:
    if x_xhsops_token != get_token():
        raise HTTPException(status_code=401, detail="bad token")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="body must be json")

    url = str(payload.get("url") or "")
    body = payload.get("body") or ""
    if not isinstance(body, str) or not body:
        raise HTTPException(status_code=400, detail="empty body")

    stamp = time.strftime("%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"
    from ..ingest import classify

    kind = classify(url)
    path = _day_dir() / f"{stamp}-{kind}.json"
    path.write_text(
        json.dumps(
            {
                "url": url,
                "page": payload.get("page"),
                "ts": payload.get("ts"),
                "received_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "body": body,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"[ingest] {kind} {len(body)} bytes -> {path.name}", flush=True)

    parsed = parse({"url": url, "body": body, "page": payload.get("page")})
    conn = store.connect()
    try:
        result = save(conn, parsed)
    finally:
        conn.close()
    print(f"[parse]  {result}", flush=True)

    return {"ok": True, "stored": path.name, **result}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    data = stats()
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>xhs-ops bridge</title>
<style>
body{{font:14px/1.6 system-ui,"Microsoft YaHei",sans-serif;background:#111;color:#eee;padding:40px;max-width:640px;margin:auto}}
code{{background:#222;padding:2px 6px;border-radius:4px}}
.ok{{color:#6ee7a8}}
</style></head><body>
<h1>xhs-ops bridge</h1>
<p class="ok">服务在运行</p>
<p>原始响应：今天 <b>{data['raw_today']}</b> 条，累计 <b>{data['raw_total']}</b> 条。</p>
<p>入库笔记：<b>{data['notes']}</b> 条，其中插件来源 <b>{data['ext_notes']}</b> 条；评论 <b>{data['comments']}</b> 条。</p>
<p>数据目录：<code>{INBOX}</code></p>
<p>插件 token：<code>{get_token()}</code></p>
</body></html>"""
