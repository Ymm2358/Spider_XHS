"""SQLite 存储层。只做读写，不做业务判断。"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Iterable, Optional

from .config import DB_PATH, ensure_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    note_id      TEXT PRIMARY KEY,
    title        TEXT,
    desc         TEXT,
    note_type    TEXT,
    publish_ts   INTEGER,
    publish_text TEXT,
    author_id    TEXT,
    author_nick  TEXT,
    liked        INTEGER DEFAULT 0,
    collected    INTEGER DEFAULT 0,
    comment      INTEGER DEFAULT 0,
    share        INTEGER DEFAULT 0,
    image_count  INTEGER DEFAULT 0,
    tags_json    TEXT,
    cover_url    TEXT,
    url          TEXT,
    keyword      TEXT,
    source       TEXT,
    first_seen   TEXT,
    last_seen    TEXT,
    raw_json     TEXT
);

CREATE INDEX IF NOT EXISTS idx_notes_keyword ON notes(keyword);
CREATE INDEX IF NOT EXISTS idx_notes_publish ON notes(publish_ts);
CREATE INDEX IF NOT EXISTS idx_notes_author ON notes(author_id);

CREATE TABLE IF NOT EXISTS note_snapshots (
    note_id    TEXT NOT NULL,
    ts         TEXT NOT NULL,
    liked      INTEGER DEFAULT 0,
    collected  INTEGER DEFAULT 0,
    comment    INTEGER DEFAULT 0,
    share      INTEGER DEFAULT 0,
    PRIMARY KEY (note_id, ts)
);

CREATE TABLE IF NOT EXISTS authors (
    author_id  TEXT PRIMARY KEY,
    nick       TEXT,
    fans       INTEGER,
    note_count INTEGER,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    run_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    started    TEXT,
    finished   TEXT,
    kind       TEXT,
    target     TEXT,
    requested  INTEGER DEFAULT 0,
    collected  INTEGER DEFAULT 0,
    inserted   INTEGER DEFAULT 0,
    status     TEXT,
    message    TEXT
);
"""


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(str(db_path or DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """轻量迁移：老库缺列时补上，避免每次改 schema 都要重建。"""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(notes)")}
    if "image_count" not in columns:
        conn.execute("ALTER TABLE notes ADD COLUMN image_count INTEGER DEFAULT 0")
        conn.commit()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def upsert_notes(conn: sqlite3.Connection, notes: Iterable[dict]) -> tuple[int, int]:
    """写入笔记并追加一条快照。返回 (新增数, 更新数)。"""
    inserted = updated = 0
    ts = now_iso()
    for note in notes:
        exists = conn.execute(
            "SELECT 1 FROM notes WHERE note_id = ?", (note["note_id"],)
        ).fetchone()
        if exists:
            conn.execute(
                """
                UPDATE notes SET
                    title = COALESCE(NULLIF(?, ''), title),
                    desc = COALESCE(NULLIF(?, ''), desc),
                    note_type = COALESCE(NULLIF(?, ''), note_type),
                    publish_ts = COALESCE(?, publish_ts),
                    publish_text = COALESCE(?, publish_text),
                    author_id = COALESCE(NULLIF(?, ''), author_id),
                    author_nick = COALESCE(NULLIF(?, ''), author_nick),
                    liked = MAX(liked, ?),
                    collected = MAX(collected, ?),
                    comment = MAX(comment, ?),
                    share = MAX(share, ?),
                    image_count = MAX(image_count, ?),
                    tags_json = COALESCE(NULLIF(?, ''), tags_json),
                    cover_url = COALESCE(NULLIF(?, ''), cover_url),
                    url = COALESCE(NULLIF(?, ''), url),
                    keyword = COALESCE(NULLIF(?, ''), keyword),
                    source = COALESCE(NULLIF(?, ''), source),
                    last_seen = ?
                WHERE note_id = ?
                """,
                (
                    note.get("title", ""),
                    note.get("desc", ""),
                    note.get("note_type", ""),
                    note.get("publish_ts"),
                    note.get("publish_text", ""),
                    note.get("author_id", ""),
                    note.get("author_nick", ""),
                    note.get("liked", 0),
                    note.get("collected", 0),
                    note.get("comment", 0),
                    note.get("share", 0),
                    note.get("image_count", 0),
                    json.dumps(note.get("tags") or [], ensure_ascii=False),
                    note.get("cover_url", ""),
                    note.get("url", ""),
                    note.get("keyword", ""),
                    note.get("source", ""),
                    ts,
                    note["note_id"],
                ),
            )
            updated += 1
        else:
            conn.execute(
                """
                INSERT INTO notes (
                    note_id, title, desc, note_type, publish_ts, publish_text,
                    author_id, author_nick, liked, collected, comment, share,
                    image_count, tags_json, cover_url, url, keyword, source, first_seen, last_seen, raw_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    note["note_id"],
                    note.get("title", ""),
                    note.get("desc", ""),
                    note.get("note_type", ""),
                    note.get("publish_ts"),
                    note.get("publish_text", ""),
                    note.get("author_id", ""),
                    note.get("author_nick", ""),
                    note.get("liked", 0),
                    note.get("collected", 0),
                    note.get("comment", 0),
                    note.get("share", 0),
                    note.get("image_count", 0),
                    json.dumps(note.get("tags") or [], ensure_ascii=False),
                    note.get("cover_url", ""),
                    note.get("url", ""),
                    note.get("keyword", ""),
                    note.get("source", ""),
                    ts,
                    ts,
                    json.dumps(note.get("raw") or {}, ensure_ascii=False)[:20000],
                ),
            )
            inserted += 1

        conn.execute(
            """
            INSERT OR REPLACE INTO note_snapshots (note_id, ts, liked, collected, comment, share)
            VALUES (?,?,?,?,?,?)
            """,
            (
                note["note_id"],
                ts,
                note.get("liked", 0),
                note.get("collected", 0),
                note.get("comment", 0),
                note.get("share", 0),
            ),
        )
    conn.commit()
    return inserted, updated


def start_run(conn: sqlite3.Connection, kind: str, target: str) -> int:
    cur = conn.execute(
        "INSERT INTO runs (started, kind, target, status) VALUES (?,?,?,?)",
        (now_iso(), kind, target, "running"),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_run(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    requested: int = 0,
    collected: int = 0,
    inserted: int = 0,
    status: str = "ok",
    message: str = "",
) -> None:
    conn.execute(
        """UPDATE runs SET finished=?, requested=?, collected=?, inserted=?, status=?, message=?
           WHERE run_id=?""",
        (now_iso(), requested, collected, inserted, status, message[:2000], run_id),
    )
    conn.commit()


def stats(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        """SELECT COUNT(*) AS notes,
                  COUNT(DISTINCT keyword) AS keywords,
                  COUNT(DISTINCT author_id) AS authors,
                  MIN(publish_ts) AS oldest,
                  MAX(publish_ts) AS newest
           FROM notes"""
    ).fetchone()
    runs = conn.execute(
        "SELECT COUNT(*) AS runs, MAX(started) AS last_run FROM runs"
    ).fetchone()
    return {**dict(row), **dict(runs)}
