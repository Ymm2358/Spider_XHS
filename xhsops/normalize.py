"""把上游返回的原始笔记结构整理成统一字段。

上游不同接口（搜索 / 推荐流 / 用户主页）字段名有差异，这里只做一次归一，
业务层永远只认这里的输出。字段缺失不报错，填默认值。
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from typing import Any, Optional

_UNIT = {"万": 10_000, "w": 10_000, "W": 10_000, "亿": 100_000_000}
_COUNT_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*([万wW亿]?)\s*\+?$")
_REL_RE = re.compile(r"(\d+)\s*(秒|分钟|小时|天|周|个月|月)前")
_DATE_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})")
_SHORT_DATE_RE = re.compile(r"^(\d{1,2})-(\d{1,2})$")
_REL_SECONDS = {"秒": 1, "分钟": 60, "小时": 3600, "天": 86_400, "周": 604_800, "个月": 2_592_000, "月": 2_592_000}


def parse_count(value: Any) -> int:
    """把 '1.2万'、'10+'、'赞' 这类展示值转成整数。"""
    if value is None or isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().replace(",", "").replace("+", "")
    if not text:
        return 0
    match = _COUNT_RE.match(text)
    if not match:
        return 0
    return int(float(match.group(1)) * _UNIT.get(match.group(2), 1))


def parse_publish_ts(text: Any, now: Optional[datetime] = None) -> Optional[int]:
    """把 '3天前' / '昨天' / '10-05' / '2026-10-05' 转成 epoch 秒。"""
    if not text:
        return None
    now = now or datetime.now()
    text = str(text).strip()
    if text in {"刚刚", "刚才"}:
        return int(now.timestamp())
    if text.startswith("昨天"):
        return int((now - timedelta(days=1)).timestamp())
    if text.startswith("前天"):
        return int((now - timedelta(days=2)).timestamp())

    rel = _REL_RE.search(text)
    if rel:
        return int((now - timedelta(seconds=int(rel.group(1)) * _REL_SECONDS[rel.group(2)])).timestamp())

    full = _DATE_RE.match(text)
    if full:
        year, month, day = (int(part) for part in full.groups())
        return int(datetime(year, month, day).timestamp())

    short = _SHORT_DATE_RE.match(text)
    if short:
        month, day = int(short.group(1)), int(short.group(2))
        candidate = datetime(now.year, month, day)
        if candidate > now + timedelta(days=1):
            candidate = candidate.replace(year=now.year - 1)
        return int(candidate.timestamp())

    return None


def _corner_text(card: dict) -> Optional[str]:
    tags = card.get("corner_tag_info") or []
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict) and tag.get("type") == "publish_time" and tag.get("text"):
                return str(tag["text"])
        for tag in tags:
            if isinstance(tag, dict) and tag.get("text"):
                return str(tag["text"])
    return None


def _first_url(cover: Any) -> str:
    if isinstance(cover, str):
        return cover
    if not isinstance(cover, dict):
        return ""
    for key in ("url_default", "url_pre", "url", "urlDefault"):
        if cover.get(key):
            return str(cover[key])
    info_list = cover.get("info_list") or []
    if isinstance(info_list, list):
        for info in info_list:
            if isinstance(info, dict) and info.get("url"):
                return str(info["url"])
    return ""


def _tags(card: dict) -> list[str]:
    result: list[str] = []
    for tag in card.get("tag_list") or []:
        if isinstance(tag, dict):
            name = tag.get("name") or tag.get("title")
            if name:
                result.append(str(name))
        elif isinstance(tag, str):
            result.append(tag)
    return result


def note_from_item(item: dict, keyword: str = "", source: str = "") -> Optional[dict]:
    """把搜索 / 推荐流 / 用户主页的单条结果转成 notes 表的一行。"""
    if not isinstance(item, dict):
        return None
    card = item.get("note_card") or item.get("noteCard") or item.get("note") or {}
    if not isinstance(card, dict):
        card = {}
    # user_posted 返回的是裸 note card，没有 note_card 包装。
    if not card and item.get("note_id"):
        card = item

    note_id = str(item.get("id") or item.get("note_id") or card.get("note_id") or "")
    if not note_id:
        return None

    user = card.get("user") or {}
    interact = card.get("interact_info") or card.get("interactInfo") or {}
    xsec_token = str(item.get("xsec_token") or card.get("xsec_token") or "")
    publish_text = _corner_text(card)
    publish_ts = parse_publish_ts(publish_text)
    if publish_ts is None:
        raw_time = card.get("time") or item.get("time")
        if isinstance(raw_time, (int, float)) and raw_time > 0:
            publish_ts = int(raw_time / 1000) if raw_time > 1e12 else int(raw_time)

    note_type = str(card.get("type") or "")
    if not note_type:
        note_type = "video" if card.get("video") else "normal"

    images = card.get("image_list") or []
    return {
        "note_id": note_id,
        "title": str(card.get("display_title") or card.get("title") or "").strip(),
        "desc": str(card.get("desc") or "").strip(),
        "note_type": note_type,
        "publish_ts": publish_ts,
        "publish_text": publish_text,
        "author_id": str(user.get("user_id") or ""),
        "author_nick": str(user.get("nickname") or user.get("nick_name") or ""),
        "liked": parse_count(interact.get("liked_count") or interact.get("likedCount")),
        "collected": parse_count(interact.get("collected_count") or interact.get("collectedCount")),
        "comment": parse_count(interact.get("comment_count") or interact.get("commentCount")),
        "share": parse_count(interact.get("shared_count") or interact.get("share_count")),
        "tags": _tags(card),
        "image_count": len(images) if isinstance(images, list) else 0,
        "cover_url": _first_url(card.get("cover")),
        "xsec_token": xsec_token,
        "url": (
            f"https://www.xiaohongshu.com/explore/{note_id}"
            + (f"?xsec_token={xsec_token}&xsec_source=pc_search" if xsec_token else "")
        ),
        "keyword": keyword,
        "source": source,
        "raw": item,
    }


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")
