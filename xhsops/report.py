"""把指标结果渲染成日报。日报只陈述数据，判断留给 agent。"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .config import REPORT_DIR, ensure_dirs
from .metrics import note_brief


def _pct(value) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.0f}%"


def _num(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render(analysis: dict) -> str:
    lines: list[str] = []
    lines.append(f"# 选题雷达 {analysis['generated_at'][:10]}")
    lines.append("")
    lines.append(
        f"样本 {analysis['total_notes']} 条，其中有发布时间 {analysis['dated_notes']} 条、"
        f"有粉丝数 {analysis['fans_known']} 条；统计窗口 {analysis['window_days']} 天。"
    )
    lines.append("")

    lines.append("## 方向对比")
    rows = []
    for item in analysis["directions"]:
        rows.append(
            [
                item["direction"],
                str(item["notes"]),
                _num(item["supply_per_day"]),
                _num(item["median_engagement"]),
                _pct(item["viral_rate"]),
                _pct(item["novice_viral_rate"]),
                _pct(item["video_share"]),
                _num(item["median_images"]),
                _num(item["blue_ocean"]),
            ]
        )
    lines.append(
        _table(
            ["方向", "笔记数", "供给/天", "中位互动", "爆款率", "素人爆款率", "视频占比", "中位图片", "蓝海指数"],
            rows,
        )
    )
    lines.append("")
    lines.append("素人爆款率 = 爆款笔记里粉丝低于阈值（默认 1 万）的作者占比，分母是已知粉丝数的爆款。蓝海指数 = 需求分位 − 供给分位，越高越值得做。")
    lines.append("")

    lines.append("## 关键词蓝海榜")
    rows = []
    for item in analysis["keywords"][:15]:
        rows.append(
            [
                item["keyword"],
                item["direction"],
                str(item["notes"]),
                _num(item["supply_per_day"]),
                _num(item["median_velocity"]),
                _pct(item["novice_viral_rate"]),
                _num(item["blue_ocean"]),
                f"{item['window_days']}天",
            ]
        )
    lines.append(
        _table(
            ["关键词", "方向", "笔记数", "供给/天", "中位涨速", "素人爆款率", "蓝海指数", "窗口"],
            rows,
        )
    )
    lines.append("")

    lines.append("## 正在起量的笔记")
    seen: set[str] = set()
    picked = []
    for item in analysis["keywords"][:10]:
        for note in item["top_notes"][:2]:
            if note["note_id"] in seen:
                continue
            seen.add(note["note_id"])
            picked.append(note)
    picked.sort(key=lambda n: n.get("z") or 0, reverse=True)
    for note in picked[:10]:
        brief = note_brief(note)
        fans = brief["author_fans"]
        fans_text = f"{fans} 粉" if fans is not None else "粉丝数未知"
        lines.append(
            f"- [{brief['title'] or '(无标题)'}]({brief['url']})  \n"
            f"  {brief['author']}（{fans_text}）· {brief['publish_text']} · "
            f"赞 {brief['liked']} / 藏 {brief['collected']} / 评 {brief['comment']} · z={brief['z']}"
        )
    lines.append("")

    lines.append("## 数据说明")
    lines.append("- 互动量来自平台展示值，可能有取整；涨速是「加权互动 / 发布小时数」的近似。")
    lines.append("- 单日数据只能看横截面，趋势判断需要连续 3 天以上的快照。")
    lines.append("- 素人爆款率只统计已补全粉丝数的爆款，样本不足时显示 —。")
    lines.append("")
    return "\n".join(lines)


def write(analysis: dict, day: str | None = None) -> tuple[Path, Path]:
    ensure_dirs()
    day = day or time.strftime("%Y-%m-%d")
    folder = REPORT_DIR / day
    folder.mkdir(parents=True, exist_ok=True)
    json_path = folder / "brief.json"
    md_path = folder / "brief.md"
    json_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render(analysis), encoding="utf-8")
    return md_path, json_path
