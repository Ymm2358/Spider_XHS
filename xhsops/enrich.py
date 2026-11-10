"""补全作者信息。粉丝数只有用户主页接口有，逐条抓成本高，所以按需补。"""

from __future__ import annotations

import random
import time

from .adapters import build_pc_api
from .normalize import parse_count


def fetch_author(api, author_id: str) -> dict | None:
    ok, _message, data = api.get_user_info(author_id)
    if not ok or not isinstance(data, dict):
        return None
    basic = data.get("basic_info") or {}
    fans = None
    for item in data.get("interactions") or []:
        if isinstance(item, dict) and item.get("type") == "fans":
            fans = parse_count(item.get("count"))
            break
    return {
        "author_id": author_id,
        "nick": str(basic.get("nickname") or ""),
        "fans": fans,
        "ip_location": str(basic.get("ip_location") or ""),
        "desc": str(basic.get("desc") or ""),
    }


def enrich(conn, api=None, limit: int = 60, delay: tuple[float, float] = (1.5, 3.0)) -> dict:
    """给还没粉丝数的作者补数据，优先补互动量高的笔记作者。"""
    api = api or build_pc_api()
    rows = conn.execute(
        """
        SELECT author_id, MAX(liked + 3 * collected + 4 * comment) AS heat
        FROM notes
        WHERE author_id != '' AND author_fans IS NULL
        GROUP BY author_id
        ORDER BY heat DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    done = failed = 0
    blocked = 0
    for index, row in enumerate(rows):
        author = fetch_author(api, row["author_id"])
        if author:
            conn.execute(
                """INSERT INTO authors (author_id, nick, fans, updated_at)
                   VALUES (?,?,?,datetime('now'))
                   ON CONFLICT(author_id) DO UPDATE SET
                     nick=excluded.nick, fans=excluded.fans, updated_at=excluded.updated_at""",
                (author["author_id"], author["nick"], author["fans"]),
            )
            if author["fans"] is not None:
                conn.execute(
                    "UPDATE notes SET author_fans = ? WHERE author_id = ?",
                    (author["fans"], author["author_id"]),
                )
            done += 1
        else:
            failed += 1
            blocked += 1
            # 40001 表示账号安全验证，继续请求只会不断触发扫码，直接停。
            if blocked >= 3:
                conn.commit()
                return {
                    "requested": len(rows),
                    "done": done,
                    "failed": failed,
                    "stopped": "连续 3 个作者触发安全验证（40001），已停止。换时间再跑，或降低频率。",
                }
        if index < len(rows) - 1:
            time.sleep(random.uniform(*delay))
    conn.commit()
    return {"requested": len(rows), "done": done, "failed": failed}
