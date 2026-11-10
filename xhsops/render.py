"""把 brief.json 渲染成可打印的 HTML，再由 export 转成 PDF / PNG。

设计原则：
- 数据只来自 brief.json，不在这里算指标。
- 图表用内联 SVG，不依赖 JS 和 CDN，离线也能渲染。
- 同一份数据出两种版式：full（A4 多页 PDF）和 card（1080x1440 分享图）。
"""

from __future__ import annotations

import html
import re
import time
from pathlib import Path
from typing import Iterable

from markdown_it import MarkdownIt

md = MarkdownIt("commonmark", {"html": False, "linkify": True})

RED = "#ff2442"
INK = "#1a1a1a"
MUTED = "#6b7280"
LINE = "#e5e7eb"

BASE_CSS = f"""
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: {INK}; background: #fff;
       font-family: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif; }}
.page {{ padding: 36px 44px; }}
h1 {{ font-size: 26px; margin: 0 0 6px; }}
h2 {{ font-size: 17px; margin: 28px 0 10px; padding-left: 10px; border-left: 4px solid {RED}; }}
.meta {{ color: {MUTED}; font-size: 12px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }}
th, td {{ padding: 6px 8px; border-bottom: 1px solid {LINE}; text-align: right; }}
th:first-child, td:first-child {{ text-align: left; }}
th {{ color: {MUTED}; font-weight: 500; }}
.note {{ font-size: 12px; color: {MUTED}; margin-top: 10px; line-height: 1.7; }}
.note b {{ color: {INK}; }}
.item {{ padding: 8px 0; border-bottom: 1px solid {LINE}; font-size: 12px; }}
.item a {{ color: {INK}; text-decoration: none; }}
.item .sub {{ color: {MUTED}; margin-top: 2px; }}
.advice {{ font-size: 13px; line-height: 1.75; }}
.advice h2 {{ border-left-color: {RED}; }}
.advice h3 {{ font-size: 14px; margin: 18px 0 6px; }}
.advice ul {{ padding-left: 20px; }}
.advice a {{ color: {MUTED}; }}
.tag {{ display: inline-block; padding: 1px 6px; border-radius: 4px; background: #f3f4f6;
        color: {MUTED}; font-size: 11px; margin-left: 6px; }}
h2 {{ break-after: avoid; }}
.item, table {{ break-inside: avoid; }}
"""


def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


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


def _diverging_bars(rows: list[dict], width: int = 720, bar: int = 22) -> str:
    """蓝海指数的双向条形图，中轴为 0。"""
    if not rows:
        return ""
    label_w = 90
    value_w = 60
    chart_w = width - label_w - value_w
    center = label_w + chart_w / 2
    height = len(rows) * (bar + 8) + 10
    parts = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">']
    parts.append(
        f'<line x1="{center}" y1="0" x2="{center}" y2="{height}" stroke="{LINE}" stroke-width="1"/>'
    )
    for index, row in enumerate(rows):
        y = index * (bar + 8) + 4
        value = float(row.get("blue_ocean") or 0)
        half = chart_w / 2
        length = max(-half, min(half, value * half))
        x = center if length >= 0 else center + length
        color = RED if value >= 0 else "#c7c9d1"
        parts.append(
            f'<text x="0" y="{y + bar * 0.72}" font-size="12" fill="{INK}">{_esc(row.get("direction"))}</text>'
        )
        parts.append(
            f'<rect x="{x:.1f}" y="{y}" width="{abs(length):.1f}" height="{bar}" rx="3" fill="{color}" opacity="0.85"/>'
        )
        parts.append(
            f'<text x="{width}" y="{y + bar * 0.72}" font-size="12" fill="{MUTED}" text-anchor="end">{value:+.2f}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _direction_table(rows: Iterable[dict]) -> str:
    head = (
        "<tr><th>方向</th><th>笔记</th><th>供给/天</th><th>中位互动</th>"
        "<th>爆款率</th><th>素人爆款率</th><th>视频占比</th><th>中位图片</th><th>蓝海</th></tr>"
    )
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{_esc(row.get('direction'))}</td>"
            f"<td>{_esc(row.get('notes'))}</td>"
            f"<td>{_num(row.get('supply_per_day'))}</td>"
            f"<td>{_num(row.get('median_engagement'))}</td>"
            f"<td>{_pct(row.get('viral_rate'))}</td>"
            f"<td>{_pct(row.get('novice_viral_rate'))}</td>"
            f"<td>{_pct(row.get('video_share'))}</td>"
            f"<td>{_num(row.get('median_images'))}</td>"
            f"<td>{_num(row.get('blue_ocean'))}</td>"
            "</tr>"
        )
    return f"<table>{head}{''.join(body)}</table>"


def _top_notes(analysis: dict, limit: int = 8) -> list[dict]:
    seen: set[str] = set()
    notes: list[dict] = []
    for item in analysis.get("keywords", []):
        for note in item.get("top_notes", []):
            note_id = note.get("note_id")
            title = (note.get("title") or "").strip()
            if not note_id or note_id in seen or len(title) < 4:
                continue
            seen.add(note_id)
            notes.append(note)
    notes.sort(key=lambda n: n.get("z") or 0, reverse=True)
    return notes[:limit]


def _note_list(notes: list[dict]) -> str:
    if not notes:
        return '<p class="note">今天没有满足条件的起量笔记。</p>'
    parts = []
    for note in notes:
        fans = note.get("author_fans")
        fans_text = f"{fans} 粉" if fans is not None else "粉丝数未知"
        parts.append(
            '<div class="item">'
            f'<a href="{_esc(note.get("url"))}">{_esc(note.get("title") or "(无标题)")}</a>'
            '<div class="sub">'
            f'{_esc(note.get("author"))}（{fans_text}）· {_esc(note.get("publish_text"))} · '
            f'赞 {_esc(note.get("liked"))} / 藏 {_esc(note.get("collected"))} / 评 {_esc(note.get("comment"))} · '
            f'z={_num(note.get("z"))}'
            "</div></div>"
        )
    return "".join(parts)


def _prepare_advice(text: str) -> str:
    """去掉重复的一级标题，把长链接收成「原文」。"""
    if not text.strip():
        return ""
    text = re.sub(r"^#\s+.*\n", "", text, count=1)
    text = re.sub(
        r"(https://www\.xiaohongshu\.com/explore/[^\s，。）)]+)",
        r"[原文](\1)",
        text,
    )
    return text


def render_full(analysis: dict, advice_md: str = "") -> str:
    directions = analysis.get("directions", [])
    top = _top_notes(analysis)
    advice_html = md.render(_prepare_advice(advice_md))
    day = (analysis.get("generated_at") or "")[:10]

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><style>{BASE_CSS}
@page {{ size: A4; margin: 12mm; }}
</style></head><body><div class="page">
<h1>选题雷达 {day}</h1>
<div class="meta">样本 {analysis.get('total_notes')} 条 · 有发布时间 {analysis.get('dated_notes')} 条 ·
有粉丝数 {analysis.get('fans_known')} 条 · 统计窗口 {analysis.get('window_days')} 天</div>

<h2>方向对比</h2>
{_diverging_bars(directions)}
{_direction_table(directions)}
<div class="note">蓝海指数 = 需求分位 − 供给分位，中轴右侧为值得做。素人爆款率只统计已知粉丝数的爆款，样本不足时显示 —。</div>

<h2>正在起量的笔记</h2>
{_note_list(top)}

<h2>选题建议</h2>
<div class="advice">{advice_html or '<p class="note">今天还没有生成建议，先跑 agent。</p>'}</div>

<div class="note">
数据来自本地采集，互动量为平台展示值，可能有取整。涨速是「加权互动 / 发布小时数」的近似，单日数据只能看横截面。
</div>
</div></body></html>"""


def _card_row(item: dict) -> str:
    value = float(item.get("blue_ocean") or 0)
    width = max(3, min(100, value * 100)) if value > 0 else 3
    color = RED if value > 0 else "#c7c9d1"
    return (
        f'<div class="row"><div class="name">{_esc(item.get("direction"))}</div>'
        f'<div class="bar"><span style="width:{width:.0f}%;background:{color}"></span></div>'
        f'<div class="val">{value:+.2f}</div></div>'
    )


def render_card(analysis: dict) -> str:
    directions = analysis.get("directions", [])[:4]
    day = (analysis.get("generated_at") or "")[:10]
    rows = "".join(
        _card_row(item)
        for item in directions
    )
    notes = _top_notes(analysis, 4)
    note_html = "".join(
        f'<li>{_esc(note.get("title") or "(无标题)")}'
        f'<span class="who">{_esc(note.get("author"))}</span></li>'
        for note in notes
    )
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><style>{BASE_CSS}
html, body {{ width: 1080px; height: 1440px; overflow: hidden; }}
.card {{ width: 1080px; height: 1440px; padding: 72px 64px; display: flex; flex-direction: column; }}
.card h1 {{ font-size: 52px; margin-bottom: 10px; }}
.card .meta {{ font-size: 22px; }}
.card .label {{ font-size: 22px; color: {MUTED}; margin: 44px 0 18px; }}
.row {{ display: flex; align-items: center; gap: 18px; margin-bottom: 18px; }}
.row .name {{ width: 160px; font-size: 26px; }}
.row .bar {{ flex: 1; height: 20px; background: #f1f2f5; border-radius: 10px; overflow: hidden; }}
.row .bar span {{ display: block; height: 100%; background: {RED}; }}
.row .val {{ width: 80px; text-align: right; font-size: 24px; color: {MUTED}; }}
.card ul {{ padding-left: 34px; font-size: 26px; line-height: 1.6; }}
.card li {{ margin-bottom: 16px; }}
.card .who {{ color: {MUTED}; font-size: 20px; margin-left: 12px; }}
.card .foot {{ margin-top: auto; font-size: 20px; color: {MUTED}; line-height: 1.6; }}
</style></head><body><div class="card">
<h1>今天做什么</h1>
<div class="meta">{day} · 样本 {analysis.get('total_notes')} 条</div>

<div class="label">方向机会（蓝海指数）</div>
{rows}

<div class="label">值得点开的笔记</div>
<ul>{note_html}</ul>

<div class="foot">数据来自本地采集，单日只能看横截面。<br>完整报告见同日 PDF。</div>
</div></body></html>"""


def write_html(content: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
