"""采集层：只负责取数和归档原始 JSON，不做指标计算。"""

from __future__ import annotations

import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Sequence

from .adapters import build_pc_api, unwrap
from .config import RAW_DIR, ensure_dirs
from .normalize import note_from_item


def archive(kind: str, target: str, payload) -> Path:
    """原始响应落盘，指标算错时可以离线重算，不必重爬。"""
    ensure_dirs()
    day = datetime.now().strftime("%Y-%m-%d")
    folder = RAW_DIR / day
    folder.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in target)[:60]
    path = folder / f"{kind}_{safe}_{int(time.time())}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def collect_search(
    keyword: str,
    limit: int = 60,
    sort: int = 0,
    note_time: int = 0,
    api=None,
    archive_raw: bool = True,
) -> list[dict]:
    """按关键词采集笔记。

    sort: 0 综合 1 最新 2 最多点赞 3 最多评论 4 最多收藏
    note_time: 0 不限 1 一天内 2 一周内 3 半年内
    """
    api = api or build_pc_api()
    data = unwrap(
        api.search_some_note(keyword, limit, sort_type_choice=sort, note_time=note_time)
    )
    items = data if isinstance(data, list) else []

    if archive_raw:
        archive(f"search_s{sort}t{note_time}", keyword, items)

    notes = [
        note_from_item(item, keyword=keyword, source=f"search:s{sort}t{note_time}")
        for item in items
    ]
    return [note for note in notes if note]


def collect_user_notes(user_url: str, api=None, archive_raw: bool = True) -> list[dict]:
    """采集某个用户主页的全部笔记，用于对标账号。"""
    api = api or build_pc_api()
    data = unwrap(api.get_user_all_notes(user_url))
    items = data if isinstance(data, list) else []
    if archive_raw:
        archive("user", user_url, items)
    notes = [note_from_item(item, keyword="", source="user") for item in items]
    return [note for note in notes if note]


def collect_homefeed(limit: int = 60, api=None, archive_raw: bool = True) -> list[dict]:
    """首页推荐流，用来观察平台正在推什么。"""
    api = api or build_pc_api()
    data = unwrap(api.get_homefeed_recommend_by_num("homefeed_recommend", limit))
    items = data if isinstance(data, list) else []
    if archive_raw:
        archive("homefeed", "recommend", items)
    notes = [note_from_item(item, keyword="", source="homefeed") for item in items]
    return [note for note in notes if note]


def collect_profile(
    keywords: Sequence[str],
    profile: Sequence[dict],
    api=None,
    delay: tuple[float, float] = (2.0, 4.5),
) -> tuple[list[dict], list[str]]:
    """按配置里的采集档位批量抓取。profile 每项形如
    {sort: 0, note_time: 0, limit: 40}。
    """
    api = api or build_pc_api()
    all_notes: list[dict] = []
    errors: list[str] = []
    total = len(keywords) * len(profile)
    done = 0
    for keyword in keywords:
        for spec in profile:
            done += 1
            sort = int(spec.get("sort", 0))
            note_time = int(spec.get("note_time", 0))
            limit = int(spec.get("limit", 40))
            try:
                all_notes.extend(
                    collect_search(keyword, limit=limit, sort=sort, note_time=note_time, api=api)
                )
            except Exception as exc:  # 单个组合失败不影响整体
                errors.append(f"{keyword} sort={sort} time={note_time}: {exc}")
            if done < total:
                time.sleep(random.uniform(*delay))
    return all_notes, errors
