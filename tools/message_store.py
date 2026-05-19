"""SQLite repository for watched Telegram groups, captured messages and digests.

Three tables only:
    - messages          — every captured group message
    - groups_watched    — list of groups/channels we monitor
    - daily_digests     — per-day per-group rolled-up relevant items

All public methods are async. Rows are immutable @dataclass(frozen=True).
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import aiosqlite

logger = logging.getLogger(__name__)

DDL = """
CREATE TABLE IF NOT EXISTS messages (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  tg_msg_id       INTEGER NOT NULL,
  chat_id         INTEGER NOT NULL,
  chat_type       TEXT    NOT NULL CHECK(chat_type IN ('group','channel')),
  sender_id       INTEGER,
  sender_name     TEXT,
  text            TEXT,
  media_kind      TEXT,
  ts              INTEGER NOT NULL,
  topic           TEXT,
  summary         TEXT,
  relevant        INTEGER,
  processed_at    INTEGER,
  UNIQUE(chat_id, tg_msg_id)
);
CREATE INDEX IF NOT EXISTS idx_messages_chat_ts       ON messages(chat_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_messages_relevant_chat ON messages(chat_id, relevant, ts DESC);

CREATE TABLE IF NOT EXISTS groups_watched (
  chat_id          INTEGER PRIMARY KEY,
  title            TEXT NOT NULL,
  enabled          INTEGER NOT NULL DEFAULT 1,
  topic_hint       TEXT,
  source_link      TEXT,
  last_scanned_at  INTEGER
);

CREATE TABLE IF NOT EXISTS daily_digests (
  date       TEXT NOT NULL,
  chat_id    INTEGER NOT NULL,
  items_json TEXT NOT NULL,
  built_at   INTEGER NOT NULL,
  PRIMARY KEY(date, chat_id)
);
"""


@dataclass(frozen=True)
class MessageRow:
    tg_msg_id: int
    chat_id: int
    chat_type: str
    sender_id: Optional[int]
    sender_name: Optional[str]
    text: Optional[str]
    media_kind: Optional[str]
    ts: int


@dataclass(frozen=True)
class GroupRow:
    chat_id: int
    title: str
    enabled: bool
    topic_hint: Optional[str]
    source_link: Optional[str]
    last_scanned_at: Optional[int]


@dataclass(frozen=True)
class StoredMessage:
    id: int
    tg_msg_id: int
    chat_id: int
    sender_id: Optional[int]
    sender_name: Optional[str]
    text: Optional[str]
    ts: int
    topic: Optional[str]
    summary: Optional[str]
    relevant: Optional[int]


class MessageStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    @asynccontextmanager
    async def _conn(self) -> AsyncIterator[aiosqlite.Connection]:
        conn = await aiosqlite.connect(self._db_path)
        try:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA journal_mode=WAL;")
            await conn.execute("PRAGMA foreign_keys=ON;")
            yield conn
            await conn.commit()
        finally:
            await conn.close()

    async def init_schema(self) -> None:
        async with self._conn() as conn:
            for stmt in DDL.split(";"):
                stmt = stmt.strip()
                if stmt:
                    await conn.execute(stmt)

    # ----------------------------------------------------------------- messages

    async def upsert_message(self, row: MessageRow) -> int:
        """Insert or update a message by (chat_id, tg_msg_id). Returns local id."""
        async with self._conn() as conn:
            await conn.execute(
                """
                INSERT INTO messages
                  (tg_msg_id, chat_id, chat_type, sender_id, sender_name,
                   text, media_kind, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, tg_msg_id) DO UPDATE SET
                  sender_id=excluded.sender_id,
                  sender_name=excluded.sender_name,
                  text=COALESCE(excluded.text, messages.text),
                  media_kind=COALESCE(excluded.media_kind, messages.media_kind),
                  ts=excluded.ts
                """,
                (
                    row.tg_msg_id, row.chat_id, row.chat_type, row.sender_id,
                    row.sender_name, row.text, row.media_kind, row.ts,
                ),
            )
            cur = await conn.execute(
                "SELECT id FROM messages WHERE chat_id=? AND tg_msg_id=?",
                (row.chat_id, row.tg_msg_id),
            )
            res = await cur.fetchone()
            return int(res["id"])

    async def update_relevance(
        self,
        local_id: int,
        relevant: bool,
        topic: Optional[str],
        summary: Optional[str],
    ) -> None:
        async with self._conn() as conn:
            await conn.execute(
                """
                UPDATE messages
                   SET relevant=?, topic=?, summary=?, processed_at=?
                 WHERE id=?
                """,
                (1 if relevant else 0, topic, summary, int(time.time()), local_id),
            )

    async def get_message_relevance(
        self, chat_id: int, tg_msg_id: int
    ) -> Optional[int]:
        async with self._conn() as conn:
            cur = await conn.execute(
                "SELECT relevant FROM messages WHERE chat_id=? AND tg_msg_id=?",
                (chat_id, tg_msg_id),
            )
            res = await cur.fetchone()
        if res is None or res["relevant"] is None:
            return None
        return int(res["relevant"])

    async def list_relevant_messages(
        self,
        *,
        since_ts: int,
        until_ts: int,
        chat_id: Optional[int] = None,
        limit: int = 500,
    ) -> list[StoredMessage]:
        sql = (
            "SELECT id, tg_msg_id, chat_id, sender_id, sender_name, text, ts,"
            "       topic, summary, relevant"
            "  FROM messages"
            " WHERE relevant=1 AND ts>=? AND ts<?"
        )
        params: list = [since_ts, until_ts]
        if chat_id is not None:
            sql += " AND chat_id=?"
            params.append(chat_id)
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        async with self._conn() as conn:
            cur = await conn.execute(sql, tuple(params))
            rows = await cur.fetchall()
        return [
            StoredMessage(
                id=int(r["id"]), tg_msg_id=int(r["tg_msg_id"]),
                chat_id=int(r["chat_id"]),
                sender_id=r["sender_id"], sender_name=r["sender_name"],
                text=r["text"], ts=int(r["ts"]),
                topic=r["topic"], summary=r["summary"],
                relevant=r["relevant"],
            )
            for r in rows
        ]

    # ------------------------------------------------------------- groups_watched

    async def upsert_group(
        self,
        *,
        chat_id: int,
        title: str,
        topic_hint: Optional[str],
        source_link: Optional[str],
        enabled: bool = True,
    ) -> None:
        async with self._conn() as conn:
            await conn.execute(
                """
                INSERT INTO groups_watched
                  (chat_id, title, enabled, topic_hint, source_link)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                  title=excluded.title,
                  enabled=excluded.enabled,
                  topic_hint=COALESCE(excluded.topic_hint, groups_watched.topic_hint),
                  source_link=COALESCE(excluded.source_link, groups_watched.source_link)
                """,
                (chat_id, title, 1 if enabled else 0, topic_hint, source_link),
            )

    async def list_groups(self, only_enabled: bool = True) -> list[GroupRow]:
        sql = "SELECT * FROM groups_watched"
        if only_enabled:
            sql += " WHERE enabled=1"
        sql += " ORDER BY title COLLATE NOCASE"
        async with self._conn() as conn:
            cur = await conn.execute(sql)
            rows = await cur.fetchall()
        return [
            GroupRow(
                chat_id=int(r["chat_id"]),
                title=r["title"],
                enabled=bool(r["enabled"]),
                topic_hint=r["topic_hint"],
                source_link=r["source_link"],
                last_scanned_at=r["last_scanned_at"],
            )
            for r in rows
        ]

    async def get_group(self, chat_id: int) -> Optional[GroupRow]:
        async with self._conn() as conn:
            cur = await conn.execute(
                "SELECT * FROM groups_watched WHERE chat_id=?", (chat_id,)
            )
            r = await cur.fetchone()
        if r is None:
            return None
        return GroupRow(
            chat_id=int(r["chat_id"]),
            title=r["title"],
            enabled=bool(r["enabled"]),
            topic_hint=r["topic_hint"],
            source_link=r["source_link"],
            last_scanned_at=r["last_scanned_at"],
        )

    async def mark_group_scanned(self, chat_id: int, ts: int) -> None:
        async with self._conn() as conn:
            await conn.execute(
                "UPDATE groups_watched SET last_scanned_at=? WHERE chat_id=?",
                (ts, chat_id),
            )

    # ------------------------------------------------------------ daily_digests

    async def save_digest(
        self, date: str, chat_id: int, items: list[dict]
    ) -> None:
        async with self._conn() as conn:
            await conn.execute(
                """
                INSERT INTO daily_digests (date, chat_id, items_json, built_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(date, chat_id) DO UPDATE SET
                  items_json=excluded.items_json,
                  built_at=excluded.built_at
                """,
                (date, chat_id, json.dumps(items, ensure_ascii=False), int(time.time())),
            )

    async def get_digest(self, date: str, chat_id: int) -> Optional[list[dict]]:
        async with self._conn() as conn:
            cur = await conn.execute(
                "SELECT items_json FROM daily_digests WHERE date=? AND chat_id=?",
                (date, chat_id),
            )
            r = await cur.fetchone()
        if r is None:
            return None
        try:
            return json.loads(r["items_json"])
        except json.JSONDecodeError:
            return []

    async def list_digest_dates(self, limit: int = 30) -> list[str]:
        async with self._conn() as conn:
            cur = await conn.execute(
                "SELECT DISTINCT date FROM daily_digests ORDER BY date DESC LIMIT ?",
                (limit,),
            )
            rows = await cur.fetchall()
        return [r["date"] for r in rows]
