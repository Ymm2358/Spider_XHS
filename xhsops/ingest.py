"""把浏览器插件送来的原始响应解析成入库结构。

插件只负责搬运，解析和判断都在这里。识别不了的接口原样归档，不报错。
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

from .normalize import note_from_item, parse_count, now_iso


def keyword_from_page(page: str) -> str:
    try:
        query = parse_qs(urlparse(page or "").query)
        return str((query.get("keyword") or [""])[0])
    except Exception:
        return ""


def classify(url: str) -> str:
    if "/v2/search/notes" in url:
        return "search"
    if "/v1/homefeed" in url:
        return "homefeed"
    if "/v1/feed" in url:
        return "feed"
    if "/comment/page" in url:
        return "comment"
    if "/user/me" in url:
        return "me"
    return "other"


def parse(payload: dict) -> dict:
    """返回 {kind, notes, comments, me}。notes/comments 已归一，可直接入库。"""
    url = str(payload.get("url") or "")
    body = payload.get("body") or ""
    page = str(payload.get("page") or "")
    kind = classify(url)

    try:
        data = json.loads(body) if isinstance(body, str) else body
    except Exception:
        return {"kind": "unparsed", "notes": [], "comments": [], "me": None}

    if not isinstance(data, dict):
        return {"kind": kind, "notes": [], "comments": [], "me": None}

    result = {"kind": kind, "notes": [], "comments": [], "me": None}
    inner = data.get("data")
    if not isinstance(inner, dict):
        return result

    if kind in ("search", "homefeed", "feed"):
        keyword = keyword_from_page(page) if kind == "search" else ""
        for item in inner.get("items") or []:
            note = note_from_item(item, keyword=keyword, source=f"ext:{kind}")
            if note:
                result["notes"].append(note)

    elif kind == "comment":
        note_id = ""
        try:
            note_id = str((parse_qs(urlparse(url).query).get("note_id") or [""])[0])
        except Exception:
            pass
        for item in inner.get("comments") or []:
            if not isinstance(item, dict):
                continue
            user = item.get("user_info") or {}
            comment_id = str(item.get("id") or "")
            if not comment_id:
                continue
            result["comments"].append(
                {
                    "comment_id": comment_id,
                    "note_id": str(item.get("note_id") or note_id),
                    "content": str(item.get("content") or "").strip(),
                    "like_count": parse_count(item.get("like_count")),
                    "author_id": str(user.get("user_id") or ""),
                    "author_nick": str(user.get("nickname") or ""),
                    "create_ts": item.get("create_time"),
                    "sub_count": parse_count(item.get("sub_comment_count")),
                    "source": "ext:comment",
                }
            )

    elif kind == "me":
        result["me"] = {
            "user_id": str(inner.get("user_id") or ""),
            "nick": str(inner.get("nickname") or inner.get("nick_name") or ""),
        }

    return result


def save(conn, parsed: dict) -> dict:
    from . import store

    inserted, updated = store.upsert_notes(conn, parsed["notes"])
    comments = store.upsert_comments(conn, parsed["comments"])
    return {
        "kind": parsed["kind"],
        "notes": len(parsed["notes"]),
        "inserted": inserted,
        "updated": updated,
        "comments": comments,
    }
