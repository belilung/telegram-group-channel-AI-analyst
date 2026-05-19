"""Scan watched Telegram groups/channels and tag each message as relevant.

For each group, iterates history in a [since_ts, until_ts) window, persists
every message, then asks the Claude classifier whether it's relevant.

Used by:
    - app.run_daily_digest (cron at DIGEST_CRON_HOUR)
    - app.supervisor (history catch-up at startup)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from telethon import TelegramClient

from app.config import get_settings
from tools.classifier import judge_group
from tools.message_store import GroupRow, MessageRow, MessageStore
from tools.telegram_client import (
    detect_media_kind,
    format_msg_link,
    iter_history,
    sender_display_name,
    with_flood_retry,
)

logger = logging.getLogger(__name__)


def _extract_text(msg: object) -> str:
    """Return the best available text — caption falls back to msg.message."""
    text: str = getattr(msg, "text", None) or getattr(msg, "message", None) or ""
    return text.strip()


def _should_skip(msg: object) -> bool:
    """Skip outgoing self-sent messages and bot-authored messages."""
    if getattr(msg, "out", False):
        return True
    sender = getattr(msg, "sender", None)
    if sender is not None and getattr(sender, "bot", False):
        return True
    return False


def _username_from_source_link(source_link: Optional[str]) -> Optional[str]:
    if not source_link:
        return None
    s = source_link.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/", "tg://resolve?domain="):
        if s.startswith(prefix):
            tail = s[len(prefix):].split("/", 1)[0].split("?", 1)[0]
            if tail and not tail.startswith("c"):
                return tail
    if s.startswith("@"):
        return s.lstrip("@")
    return None


@dataclass(frozen=True)
class ScannedItem:
    tg_msg_id: int
    ts: int
    sender_name: Optional[str]
    topic: Optional[str]
    summary: Optional[str]
    link: str


async def _classify_one(
    store: MessageStore,
    local_id: int,
    text: str,
    topic_hint: str,
    sem: asyncio.Semaphore,
) -> tuple[int, bool, Optional[str], Optional[str]]:
    async with sem:
        verdict = await judge_group(text, topic_hint)
    await store.update_relevance(local_id, verdict.relevant, verdict.topic, verdict.summary)
    return local_id, verdict.relevant, verdict.topic, verdict.summary


async def scan_group(
    client: TelegramClient,
    store: MessageStore,
    group: GroupRow,
    since_ts: int,
    until_ts: int,
) -> list[ScannedItem]:
    """Scan one group in [since_ts, until_ts). Returns relevant items sorted by ts."""
    settings = get_settings()
    max_messages = settings.max_msgs_per_group
    min_text_len = settings.min_group_text_len
    sem = asyncio.Semaphore(settings.classify_concurrency)

    fetched = 0
    skipped_existing = 0
    pre_relevant: list[tuple[int, dict]] = []
    classify_tasks: list[asyncio.Task[tuple[int, bool, Optional[str], Optional[str]]]] = []
    items_by_local_id: dict[int, dict] = {}

    group_username = _username_from_source_link(group.source_link)

    async def _collect() -> None:
        nonlocal fetched, skipped_existing
        async for msg in iter_history(client, group.chat_id, since_ts, until_ts, max_messages):
            fetched += 1
            if _should_skip(msg):
                continue
            text = _extract_text(msg)
            ts = int(msg.date.timestamp()) if msg.date else 0

            existing = await store.get_message_relevance(group.chat_id, msg.id)
            row = MessageRow(
                tg_msg_id=msg.id,
                chat_id=group.chat_id,
                chat_type="group",
                sender_id=getattr(msg, "sender_id", None),
                sender_name=sender_display_name(msg),
                text=text or None,
                media_kind=detect_media_kind(msg),
                ts=ts,
            )
            local_id = await store.upsert_message(row)

            if existing is not None:
                skipped_existing += 1
                if existing == 1:
                    pre_relevant.append((local_id, {
                        "tg_msg_id": msg.id,
                        "ts": ts,
                        "sender_name": row.sender_name,
                        "link": format_msg_link(group.chat_id, msg.id, username=group_username),
                    }))
                continue

            if not text or len(text) < min_text_len:
                await store.update_relevance(local_id, False, None, None)
                continue

            items_by_local_id[local_id] = {
                "tg_msg_id": msg.id,
                "ts": ts,
                "sender_name": row.sender_name,
                "link": format_msg_link(group.chat_id, msg.id, username=group_username),
            }
            classify_tasks.append(asyncio.create_task(
                _classify_one(store, local_id, text, group.topic_hint or "", sem)
            ))

    await with_flood_retry(_collect)

    logger.info(
        "Scanned %s (chat_id=%s): fetched=%s classify=%s skipped_existing=%s cached_relevant=%s",
        group.title, group.chat_id, fetched, len(classify_tasks),
        skipped_existing, len(pre_relevant),
    )

    relevant: list[ScannedItem] = []
    for local_id, meta in pre_relevant:
        async with store._conn() as conn:  # noqa: SLF001
            cur = await conn.execute(
                "SELECT topic, summary FROM messages WHERE id=?", (local_id,)
            )
            stored_row = await cur.fetchone()
        topic = stored_row["topic"] if stored_row else None
        summary = stored_row["summary"] if stored_row else None
        relevant.append(ScannedItem(
            tg_msg_id=meta["tg_msg_id"], ts=meta["ts"],
            sender_name=meta["sender_name"],
            topic=topic, summary=summary, link=meta["link"],
        ))

    for fut in asyncio.as_completed(classify_tasks):
        local_id, is_relevant, topic, summary = await fut
        meta = items_by_local_id.get(local_id)
        if not meta or not is_relevant:
            continue
        relevant.append(ScannedItem(
            tg_msg_id=meta["tg_msg_id"], ts=meta["ts"],
            sender_name=meta["sender_name"],
            topic=topic, summary=summary, link=meta["link"],
        ))

    relevant.sort(key=lambda x: x.ts)
    return relevant
