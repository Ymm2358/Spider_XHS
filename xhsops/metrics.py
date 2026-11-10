"""指标层：全部是确定性计算，不调用模型。

所有分数都用于排序和比较，不追求绝对值准确：
- 互动量是平台展示值，可能有取整和延迟；
- 涨速用「互动 / 发布小时数」近似，只有多天快照后才精确。
"""

from __future__ import annotations

import json
import math
import statistics
import time
from typing import Iterable, Optional, Sequence

from .config import load_yaml

EPS = 1e-9


def weights() -> dict:
    data = load_yaml("weights.yml")
    return {
        "liked": 1,
        "collected": 3,
        "comment": 4,
        "share": 2,
        **((data.get("engagement") or {})),
    }


def engagement(note: dict, w: Optional[dict] = None) -> float:
    w = w or weights()
    return (
        note.get("liked", 0) * w["liked"]
        + note.get("collected", 0) * w["collected"]
        + note.get("comment", 0) * w["comment"]
        + note.get("share", 0) * w["share"]
    )


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    pos = (len(ordered) - 1) * max(0.0, min(1.0, q))
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    return float(ordered[low] + (ordered[high] - ordered[low]) * (pos - low))


def median(values: Sequence[float]) -> float:
    return float(statistics.median(values)) if values else 0.0


def mad(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    med = median(values)
    return median([abs(value - med) for value in values])


def age_hours(publish_ts: Optional[int], now: Optional[float] = None) -> Optional[float]:
    if not publish_ts:
        return None
    return max(0.0, ((now or time.time()) - publish_ts) / 3600.0)


def velocity(eng: float, hours: Optional[float]) -> float:
    """每小时加权互动。少于 6 小时按 6 小时算，避免刚发布的笔记分数虚高。"""
    if hours is None:
        return 0.0
    return eng / max(hours, 6.0)


def load_notes(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM notes").fetchall()
    notes = []
    for row in rows:
        item = dict(row)
        try:
            item["tags"] = json.loads(item.get("tags_json") or "[]")
        except Exception:
            item["tags"] = []
        notes.append(item)
    return notes


def _bucket(hours: float, buckets: Sequence[float]) -> int:
    for index, edge in enumerate(buckets):
        if hours <= edge:
            return index
    return len(buckets)


def _zscore(values: Sequence[float]) -> list[float]:
    """在 log1p 空间算稳健 z。互动量是重尾分布，直接算 z 会被个别爆款拉爆。

    低互动关键词里大量笔记 velocity 为 0，MAD 会退化成 0，此时必须给 scale
    一个下限，否则单个非零样本会算出上百的 z，完全不可比。
    """
    transformed = [math.log1p(max(0.0, value)) for value in values]
    med = median(transformed)
    scale = 1.4826 * mad(transformed)
    if scale < EPS:
        scale = statistics.pstdev(transformed) if len(transformed) > 1 else 0.0
    scale = max(scale, 0.35)
    return [max(-20.0, min(20.0, (value - med) / scale)) for value in transformed]


def _decorate(notes: Iterable[dict], w: dict, buckets: Sequence[float], now: float) -> list[dict]:
    decorated = []
    for note in notes:
        hours = age_hours(note.get("publish_ts"), now)
        eng = engagement(note, w)
        item = dict(note)
        item["engagement"] = eng
        item["age_hours"] = hours
        item["velocity"] = velocity(eng, hours)
        item["bucket"] = _bucket(hours, buckets) if hours is not None else None
        decorated.append(item)
    return decorated


def _attach_z(notes: list[dict]) -> None:
    """按 (关键词, 笔记类型, 年龄段) 分组算稳健 z；组内样本不足时退回关键词级。"""
    groups: dict[tuple, list[dict]] = {}
    for note in notes:
        key = (note.get("keyword"), note.get("note_type"), note.get("bucket"))
        groups.setdefault(key, []).append(note)
    for group in groups.values():
        if len(group) < 8:
            continue
        for note, z in zip(group, _zscore([n["velocity"] for n in group])):
            note["z"] = z
    fallback: dict[str, list[dict]] = {}
    for note in notes:
        if "z" not in note:
            fallback.setdefault(note.get("keyword") or "", []).append(note)
    for group in fallback.values():
        if len(group) < 5:
            for note in group:
                note.setdefault("z", 0.0)
            continue
        for note, z in zip(group, _zscore([n["velocity"] for n in group])):
            note["z"] = z
    for note in notes:
        note.setdefault("z", 0.0)


def summarize_keyword(notes: list[dict], viral_z: float, novice_fans: int) -> dict:
    dated = [n for n in notes if n.get("age_hours") is not None]
    velocities = [n["velocity"] for n in dated]
    engagements = [n["engagement"] for n in notes]
    viral = [n for n in dated if n.get("z", 0) >= viral_z and n["engagement"] >= 200]
    viral_with_fans = [n for n in viral if n.get("author_fans") is not None]
    novice_viral = [n for n in viral_with_fans if (n.get("author_fans") or 0) < novice_fans]

    return {
        "notes": len(notes),
        "dated": len(dated),
        "median_engagement": round(median(engagements), 1),
        "p90_engagement": round(percentile(engagements, 0.9), 1),
        "median_velocity": round(median(velocities), 2),
        "viral_count": len(viral),
        "viral_rate": round(len(viral) / len(dated), 3) if dated else 0.0,
        "viral_with_fans": len(viral_with_fans),
        "novice_viral_rate": round(len(novice_viral) / len(viral_with_fans), 3) if viral_with_fans else None,
        "video_share": round(sum(1 for n in notes if n.get("note_type") == "video") / len(notes), 3) if notes else 0.0,
        "median_images": round(median([n.get("image_count") or 0 for n in notes if n.get("note_type") != "video"]), 1),
        "top_notes": sorted(
            [
                n
                for n in dated
                if n["engagement"] >= 100 and (n.get("liked") or 0) >= 20 and (n.get("age_hours") or 0) >= 3
            ],
            key=lambda n: n["z"],
            reverse=True,
        )[:5],
    }


def analyze(conn, window_days: int = 7, min_sample: int = 30) -> dict:
    config = load_yaml("weights.yml")
    cohort = config.get("cohort") or {}
    buckets = cohort.get("age_buckets_hours") or [72, 168, 720]
    viral_z = float(cohort.get("viral_z", 2.0))
    novice_fans = int(config.get("novice_fans", 10000))

    all_notes = load_notes(conn)
    now = time.time()
    decorated = _decorate(all_notes, weights(), buckets, now)
    _attach_z(decorated)

    cutoff = now - window_days * 86400
    recent = [n for n in decorated if (n.get("publish_ts") or 0) >= cutoff]

    keywords = sorted({n.get("keyword") or "" for n in decorated if n.get("keyword")})
    direction_map = {}
    for item in load_yaml("keywords.yml").get("directions") or []:
        for kw in item.get("keywords") or []:
            direction_map[kw] = item.get("name") or "未分组"

    per_keyword = {}
    for keyword in keywords:
        sample_all = [n for n in decorated if n.get("keyword") == keyword]
        sample_recent = [n for n in sample_all if (n.get("publish_ts") or 0) >= cutoff]
        if len(sample_recent) >= 20:
            sample, window_used = sample_recent, window_days
        else:
            sample, window_used = sample_all, 30
        if not sample:
            continue
        summary = summarize_keyword(sample, viral_z, novice_fans)
        summary["keyword"] = keyword
        summary["direction"] = direction_map.get(keyword, "未分组")
        summary["window_days"] = window_used
        summary["supply_per_day"] = round(
            sum(1 for n in sample_all if (n.get("publish_ts") or 0) >= now - 7 * 86400) / 7, 2
        )
        per_keyword[keyword] = summary

    _attach_blue_ocean(per_keyword)

    directions: dict[str, list[dict]] = {}
    for summary in per_keyword.values():
        directions.setdefault(summary["direction"], []).append(summary)

    direction_rows = []
    for name, items in directions.items():
        if name == "未分组" and len(directions) > 1:
            continue
        direction_rows.append(
            {
                "direction": name,
                "keywords": [item["keyword"] for item in items],
                "notes": sum(item["notes"] for item in items),
                "supply_per_day": round(sum(item["supply_per_day"] for item in items), 2),
                "median_engagement": round(median([item["median_engagement"] for item in items]), 1),
                "median_velocity": round(median([item["median_velocity"] for item in items]), 2),
                "viral_rate": round(median([item["viral_rate"] for item in items]), 3),
                "novice_viral_rate": _median_optional([item["novice_viral_rate"] for item in items]),
                "video_share": round(median([item["video_share"] for item in items]), 3),
                "median_images": round(median([item["median_images"] for item in items]), 1),
                "blue_ocean": _median_optional([item["blue_ocean"] for item in items]) or 0.0,
                "top_notes": [n for item in items for n in item["top_notes"]][:5],
            }
        )
    direction_rows.sort(key=lambda row: (row["novice_viral_rate"] or 0, row["blue_ocean"]), reverse=True)

    return {
        "schema_version": "1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "window_days": window_days,
        "viral_z": viral_z,
        "novice_fans": novice_fans,
        "total_notes": len(decorated),
        "dated_notes": sum(1 for n in decorated if n.get("age_hours") is not None),
        "fans_known": sum(1 for n in decorated if n.get("author_fans") is not None),
        "directions": direction_rows,
        "keywords": sorted(
            [row for row in per_keyword.values() if row.get("direction") != "未分组"],
            key=lambda row: row.get("blue_ocean") or 0,
            reverse=True,
        ),
    }


def _median_optional(values: Sequence[Optional[float]]) -> Optional[float]:
    clean = [value for value in values if value is not None]
    return round(median(clean), 3) if clean else None


def _attach_blue_ocean(per_keyword: dict[str, dict]) -> None:
    """需求分位减供给分位。值越高，说明看的人多、写的人少。"""
    if not per_keyword:
        return
    demands = [item["median_velocity"] for item in per_keyword.values()]
    supplies = [item["supply_per_day"] for item in per_keyword.values()]
    for item in per_keyword.values():
        demand_rank = _rank(demands, item["median_velocity"])
        supply_rank = _rank(supplies, item["supply_per_day"])
        item["blue_ocean"] = round(demand_rank - supply_rank, 3)


def _rank(values: Sequence[float], value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    below = sum(1 for v in ordered if v < value)
    equal = sum(1 for v in ordered if v == value)
    return (below + 0.5 * equal) / len(ordered)


def note_brief(note: dict) -> dict:
    """报告里引用笔记时统一用这个结构，保证 agent 拿到的字段稳定。"""
    return {
        "note_id": note.get("note_id"),
        "title": note.get("title"),
        "url": note.get("url"),
        "author": note.get("author_nick"),
        "author_fans": note.get("author_fans"),
        "publish_text": note.get("publish_text"),
        "liked": note.get("liked"),
        "collected": note.get("collected"),
        "comment": note.get("comment"),
        "engagement": round(note.get("engagement") or 0, 1),
        "z": round(note.get("z") or 0, 2),
        "images": note.get("image_count"),
        "type": note.get("note_type"),
    }
