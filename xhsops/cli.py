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


def _keywords_for(args: argparse.Namespace) -> list[str]:
    from .config import load_yaml

    if args.keyword:
        return list(args.keyword)
    data = load_yaml("keywords.yml")
    directions = data.get("directions") or []
    if not args.direction:
        return []
    if args.direction == "all":
        return [kw for item in directions for kw in (item.get("keywords") or [])]
    matched = [item for item in directions if item.get("name") == args.direction]
    return [kw for item in matched for kw in (item.get("keywords") or [])]


def _profile_for(args: argparse.Namespace) -> list[dict]:
    from .config import load_yaml

    if args.sorts:
        sorts = [int(s) for s in args.sorts.split(",") if s.strip()]
        return [{"sort": sort, "note_time": 0, "limit": args.limit} for sort in sorts]
    data = load_yaml("keywords.yml")
    return data.get("profile") or [{"sort": 0, "note_time": 0, "limit": args.limit}]


def cmd_collect(args: argparse.Namespace) -> int:
    from .collect import collect_profile, collect_user_notes

    conn = store.connect()
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

    keywords = _keywords_for(args)
    if not keywords:
        print("需要 --keyword、--direction 或 --user", file=sys.stderr)
        return 2

    profile = _profile_for(args)
    run_id = store.start_run(conn, "search", ",".join(keywords))
    try:
        notes, errors = collect_profile(keywords, profile)
        inserted, updated = store.upsert_notes(conn, notes)
        store.finish_run(
            conn,
            run_id,
            requested=len(keywords) * len(profile) * max(int(p.get("limit", 0)) for p in profile),
            collected=len(notes),
            inserted=inserted,
            status="ok" if not errors else "partial",
            message="; ".join(errors),
        )
        _emit(
            {
                "ok": not errors,
                "keywords": len(keywords),
                "profile": profile,
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


def cmd_enrich(args: argparse.Namespace) -> int:
    from .enrich import enrich

    conn = store.connect()
    result = enrich(conn, limit=args.limit, allow_verify=args.verify)
    result["ok"] = True
    _emit(result, args.json)
    return 0


def cmd_brief(args: argparse.Namespace) -> int:
    from .metrics import analyze
    from . import report

    conn = store.connect()
    analysis = analyze(conn, window_days=args.days)
    md_path, json_path = report.write(analysis)
    if args.json:
        _print_json(analysis)
    else:
        print(f"日报：{md_path}")
        print(f"数据：{json_path}")
        print(f"样本 {analysis['total_notes']} 条，方向 {len(analysis['directions'])} 个")
        for row in analysis["directions"]:
            print(
                f"  {row['direction']:<6} 笔记 {row['notes']:>4}  "
                f"素人爆款率 {_fmt(row['novice_viral_rate'])}  蓝海 {_fmt(row['blue_ocean'])}"
            )
    return 0


def _fmt(value) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.0f}%" if isinstance(value, float) and abs(value) <= 1 else f"{value:.2f}"


def cmd_batch(args: argparse.Namespace) -> int:
    """逐关键词起子进程采集。单个关键词卡住时超时终止，不影响其余关键词。"""
    import subprocess

    keywords = _keywords_for(args)
    if not keywords:
        print("需要 --keyword 或 --direction", file=sys.stderr)
        return 2

    results = []
    errors = []
    for index, keyword in enumerate(keywords, start=1):
        cmd = [sys.executable, "-m", "xhsops", "collect", "--keyword", keyword, "--json", "--limit", str(args.limit)]
        if args.sorts:
            cmd += ["--sorts", args.sorts]
        started = time.perf_counter()
        stdout = stderr = ""
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            try:
                stdout, stderr = proc.communicate(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                # 必须连子进程树一起杀：venv 的 python.exe 会再起一个真实的 python，
                # 只杀父进程时管道不关闭，communicate 会一直等下去。
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                )
                try:
                    proc.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
                raise
            payload = _parse_json(stdout)
            elapsed = round(time.perf_counter() - started, 1)
            if payload:
                payload["keyword"] = keyword
                payload["seconds"] = elapsed
                results.append(payload)
                if payload.get("errors"):
                    errors.extend(f"{keyword}: {item}" for item in payload["errors"])
                print(
                    f"[{index}/{len(keywords)}] {keyword}  {elapsed}s  "
                    f"采集 {payload.get('collected', 0)}  新增 {payload.get('inserted', 0)}",
                    flush=True,
                )
            else:
                errors.append(f"{keyword}: 子进程无输出 {stderr[-300:]}")
                print(f"[{index}/{len(keywords)}] {keyword}  无输出", flush=True)
        except subprocess.TimeoutExpired:
            errors.append(f"{keyword}: 超过 {args.timeout}s 未完成，已终止")
            print(f"[{index}/{len(keywords)}] {keyword}  超时终止", flush=True)
        if index < len(keywords) and args.cooldown:
            time.sleep(args.cooldown)

    summary = {
        "ok": not errors,
        "keywords": len(keywords),
        "collected": sum(item.get("collected", 0) for item in results),
        "inserted": sum(item.get("inserted", 0) for item in results),
        "errors": errors,
        "results": results,
    }
    if args.json:
        _print_json(summary)
    else:
        _emit({key: value for key, value in summary.items() if key != "results"}, False)
    return 0 if not errors else 1


def _parse_json(text: str) -> Optional[dict]:
    text = (text or "").strip()
    if not text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    try:
        return json.loads(text[start:])
    except Exception:
        return None


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .web.app import get_token

    token = get_token()
    print(f"本地服务：http://127.0.0.1:{args.port}")
    print(f"插件 token：{token}")
    print("把 token 填进插件弹窗，然后打开小红书页面。Ctrl+C 停止。")
    uvicorn.run("xhsops.web.app:app", host="127.0.0.1", port=args.port, log_level="warning")
    return 0


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
    collect.add_argument("--direction", help="按 config/keywords.yml 的方向采集，all 表示全部")
    collect.add_argument("--user", help="用户主页链接")
    collect.add_argument("--limit", type=int, default=40)
    collect.add_argument("--sorts", help="临时覆盖采集档位，如 0,2,1；不传则用 keywords.yml 的 profile")
    collect.set_defaults(func=cmd_collect)

    enrich = sub.add_parser("enrich", help="补全作者粉丝数")
    enrich.add_argument("--limit", type=int, default=60, help="本次最多补多少个作者")
    enrich.add_argument("--verify", action="store_true", help="触发风控时扫码验证；默认跳过，避免卡 180 秒")
    enrich.set_defaults(func=cmd_enrich)

    batch = sub.add_parser("batch", help="逐关键词采集，单个超时不影响整体")
    batch.add_argument("--keyword", action="append", help="可重复传入多个关键词")
    batch.add_argument("--direction", help="按 keywords.yml 的方向采集，all 表示全部")
    batch.add_argument("--limit", type=int, default=40)
    batch.add_argument("--sorts", help="临时覆盖采集档位，如 0,2,1")
    batch.add_argument("--timeout", type=int, default=180, help="单个关键词的超时秒数")
    batch.add_argument("--cooldown", type=int, default=8, help="关键词之间的冷却秒数")
    batch.set_defaults(func=cmd_batch)

    status = sub.add_parser("status", help="查看库存与最近任务")
    status.set_defaults(func=cmd_status)

    brief = sub.add_parser("brief", help="生成日报（Markdown + JSON）")
    brief.add_argument("--days", type=int, default=7, help="统计窗口，默认 7 天")
    brief.set_defaults(func=cmd_brief)

    serve = sub.add_parser("serve", help="启动本地桥接服务，给浏览器插件用")
    serve.add_argument("--port", type=int, default=8787)
    serve.set_defaults(func=cmd_serve)

    # 让 --json 在子命令前后都能用：子命令里用 SUPPRESS，避免覆盖顶层已经解析出的值。
    for subparser in (doctor, collect, enrich, batch, status, brief):
        subparser.add_argument(
            "--json", action="store_true", default=argparse.SUPPRESS, help="输出 JSON，供 agent 解析"
        )

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
    # 上游每个失败都会打完整 traceback，批量跑时会把终端刷爆；需要排查时用 --debug 打开。
    from loguru import logger

    logger.remove()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
