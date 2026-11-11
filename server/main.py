"""单进程入口：engine + local 路由，托管前端构建产物。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "spider_xhs"
if VENDOR.exists() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from server.engine.main import create_app  # noqa: E402

app: FastAPI = create_app()

# 前端构建产物存在时由后端托管，一个端口就能用。
_dist = ROOT / "web" / "dist"
if (_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        """SPA 回退：非 /api 路径都返回 index.html，交给前端路由。"""
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = _dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")


def main() -> int:
    import uvicorn

    from server.engine.core.config import get_settings

    settings = get_settings()
    host = "127.0.0.1"
    port = int(settings.server_port or 8000)
    print(f"xhs-ops 后端：http://{host}:{port}")
    print(f"接口文档：http://{host}:{port}/docs")
    uvicorn.run("server.main:app", host=host, port=port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
