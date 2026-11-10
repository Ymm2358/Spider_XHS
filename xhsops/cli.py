"""命令行入口：python -m xhsops <command>"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Optional

from . import __version__, store
from .config import DB_PATH, ROOT, ensure_dirs, load_env, pc_cookie
from .adapters import UpstreamError, build_pc_api

RISK_HINTS = ("461", "471", "406", "风控", "verify", "captcha")
LOGIN_HINTS = ("-100", "登录", "login", "session", "未登录", "401")


def _classify(message: str) -> str:
    low = message.lower()
    if any(hint in low for hint in RISK_HINTS):
        return "疑似风控拦截（签名或设备指纹过期）"
    if any(hint in low for hint in LOGIN_HINTS):
        return "疑似登录态失效（Cookie 过期）"
    return "未知错误"


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def cmd_doctor(args: argparse.Namespace) -> int:
    ensure_dirs()
    report: dict[str, Any] = {"version": __version__, "root": str(ROOT), "steps": []}

    def record(name: str, ok: bool, seconds: float, detail: str = "") -> None:
        report["steps"].append(
            {"step": name, "ok": ok, "seconds": round(seconds, 2), "detail": detail}
        )

    started = time.perf_counter()
    load_env()
    env_file = ROOT / ".env"
    record(".env 文件", env_file.exists(), time.perf_counter() - started, str(env_file))

    started = time.perf_counter()
    try:
        cookie = pc_cookie()
        record("Cookie 完整性", True, time.perf_counter() - started, f"长度 {len(cookie)}")
    except Exception as exc:
        record("Cookie 完整性", False, time.perf_counter() - started, str(exc))
        report["ok"] = False
        _print_json(report) if args.json else _print_human(report)
        return 1

    started = time.perf_counter()
    try:
        api = build_pc_api(cookie)
        record("登录态 user/me", True, time.perf_counter() - started, "签名与 Cookie 均通过")
    except Exception as exc:
        message = str(exc)
        record("登录态 user/me", False, time.perf_counter() - started, f"{message} → {_classify(message)}")
        report["ok"] = False
        _print_json(report) if args.json else _print_human(report)
        return 2

    keyword = args.keyword or "摄影"
    started = time.perf_counter()
    try:
        data = api.search_some_note(keyword, args.limit)
        success, message, items = data
        if not success:
            raise UpstreamError(str(message))
        record("搜索接口", True, time.perf_counter() - started, f"关键词「{keyword}」返回 {len(items)} 条")
        report["sample"] = _summarize(items)
        if args.dump:
            dump_path = ROOT / "xhsops" / "docs" / "probe-sample.json"
            dump_path.parent.mkdir(parents=True, exist_ok=True)
            dump_path.write_text(json.dumps(items[:3], ensure_ascii=False, indent=2), encoding="utf-8")
            report["dump"] = str(dump_path)
    except Exception as exc:
        message = str(exc)
        record("搜索接口", False, time.perf_counter() - started, f"{message} → {_classify(message)}")
        report["ok"] = False
        _print_json(report) if args.json else _print_human(report)
        return 3

    report["ok"] = True
    _print_json(report) if args.json else _print_human(report)
    return 0


def _summarize(items: list) -> dict:
    if not items:
        return {"count": 0}
    first = items[0] if isinstance(items[0], dict) else {}
    card = first.get("note_card") or {}
    return {
        "count": len(items),
        "item_keys": sorted(first.keys()),
        "note_card_keys": sorted(card.keys()) if isinstance(card, dict) else [],
        "sample_title": (card.get("display_title") or "") if isinstance(card, dict) else "",
        "sample_interact": (card.get("interact_info") or {}) if isinstance(card, dict) else {},
    }


def _print_human(report: dict) -> None:
    print(f"xhsops doctor  v{report['version']}")
    print(f"项目目录：{report['root']}")
    print("-" * 56)
    for step in report["steps"]:
        mark = "OK  " if step["ok"] else "FAIL"
        print(f"[{mark}] {step['step']:<14} {step['seconds']:>5.2f}s  {step['detail']}")
    print("-" * 56)
    sample = report.get("sample") or {}
    if sample.get("count"):
        print(f"样例：{sample.get('sample_title') or '(无标题)'}  互动 {sample.get('sample_interact')}")
        print(f"顶层字段：{', '.join(sample.get('item_keys') or [])}")
        print(f"note_card 字段：{', '.join(sample.get('note_card_keys') or [])}")
    if report.get("dump"):
        print(f"原始样例已写入：{report['dump']}")
    print("结论：" + ("可以开始采集" if report.get("ok") else "未通过，先解决上面的 FAIL"))


def cmd_collect(args: argparse.Namespace) -> int:
    from .collect import collect_keywords, collect_search, collect_user_notes

    conn = store.connect()
    keywords = args.keyword or []
    if args.user:
        run_id = store.start_run(conn, "user", args.user)
        try:
            notes = collect_user_notes(args.user)
            inserted, updated = store.upsert_notes(conn, notes)
            store.finish_run(conn, run_id, collected=len(notes), inserted=inserted)
            _emit({"ok": True, "source": "user", "collected": len(notes), "inserted": inserted, "updated": updated}, args.json)
            return 0
        except Exception as exc:
            store.finish_run(conn, run_id, status="error", message=str(exc))
            _emit({"ok": False, "error": str(exc)}, args.json)
            return 1

    if not keywords:
        print("需要 --keyword 或 --user", file=sys.stderr)
        return 2

    sorts = tuple(int(s) for s in args.sorts.split(",") if s.strip())
    run_id = store.start_run(conn, "search", ",".join(keywords))
    try:
        notes, errors = collect_keywords(keywords, limit=args.limit, sorts=sorts)
        inserted, updated = store.upsert_notes(conn, notes)
        store.finish_run(
            conn,
            run_id,
            requested=len(keywords) * len(sorts) * args.limit,
            collected=len(notes),
            inserted=inserted,
            status="ok" if not errors else "partial",
            message="; ".join(errors),
        )
        _emit(
            {
                "ok": not errors,
                "keywords": keywords,
                "sorts": sorts,
                "collected": len(notes),
                "inserted": inserted,
                "updated": updated,
                "errors": errors,
            },
            args.json,
        )
        return 0 if not errors else 1
    except Exception as exc:
        store.finish_run(conn, run_id, status="error", message=str(exc))
        _emit({"ok": False, "error": str(exc)}, args.json)
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    conn = store.connect()
    data = store.stats(conn)
    data["db"] = str(DB_PATH)
    data["db_mb"] = round(DB_PATH.stat().st_size / 1024 / 1024, 2) if DB_PATH.exists() else 0
    recent = [dict(row) for row in conn.execute(
        "SELECT started, kind, target, collected, inserted, status FROM runs ORDER BY run_id DESC LIMIT 5"
    )]
    data["recent_runs"] = recent
    _emit(data, args.json)
    return 0


def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        _print_json(payload)
        return
    for key, value in payload.items():
        if key == "recent_runs":
            print("最近任务：")
            for row in value:
                print(f"  {row['started']}  {row['kind']:<8} {row['target'][:24]:<24} 采集 {row['collected']} 新增 {row['inserted']}  {row['status']}")
        else:
            print(f"{key}: {value}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xhsops", description="小红书选题雷达")
    parser.add_argument("--json", action="store_true", help="输出 JSON，供 agent 解析")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="检查 Cookie 与签名是否可用")
    doctor.add_argument("--keyword", default="摄影")
    doctor.add_argument("--limit", type=int, default=20)
    doctor.add_argument("--dump", action="store_true", help="把前 3 条原始结果写入 xhsops/docs/probe-sample.json")
    doctor.set_defaults(func=cmd_doctor)

    collect = sub.add_parser("collect", help="采集关键词或用户主页")
    collect.add_argument("--keyword", action="append", help="可重复传入多个关键词")
    collect.add_argument("--user", help="用户主页链接")
    collect.add_argument("--limit", type=int, default=60)
    collect.add_argument("--sorts", default="0", help="逗号分隔：0 综合 1 最新 2 最多点赞")
    collect.set_defaults(func=cmd_collect)

    status = sub.add_parser("status", help="查看库存与最近任务")
    status.set_defaults(func=cmd_status)

    return parser


def _configure_stdio() -> None:
    """Windows 控制台默认 GBK，中文和 JSON 都会乱码，统一成 UTF-8。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main(argv: Optional[list[str]] = None) -> int:
    _configure_stdio()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
