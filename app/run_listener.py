"""Realtime Telegram listener for group/channel messages.

Connects via Telethon, subscribes to NewMessage events in any watched group,
persists each message, and (when REALTIME_AI_FILTER=true) runs Claude
classification in the background, populating `messages.topic/summary/relevant`.

Run standalone:
    python -m app.run_listener

In production, use `python -m app.supervisor` which combines this with the
scheduler and the dashboard.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from telethon import TelegramClient, events
from telethon.tl.custom.message import Message

from app.config import Settings, get_settings
from tools.classifier import judge_group
from tools.message_store import MessageRow, MessageStore
from tools.telegram_client import (
    build_client,
    detect_media_kind,
    sender_display_name,
)

logger = logging.getLogger(__name__)


class _WatchedGroupCache:
    """Refreshes once a minute so groups added at runtime get picked up."""

    def __init__(self, store: MessageStore, refresh_interval_s: float = 60.0) -> None:
        self._store = store
        self._interval = refresh_interval_s
        self._cache: dict[int, tuple[str, Optional[str]]] = {}
        self._last_refresh = 0.0
        self._lock = asyncio.Lock()

    async def get(self, chat_id: int) -> Optional[tuple[str, Optional[str]]]:
        now = time.monotonic()
        if now - self._last_refresh > self._interval:
            async with self._lock:
                if now - self._last_refresh > self._interval:
                    await self._refresh()
                    self._last_refresh = now
        return self._cache.get(chat_id)

    async def _refresh(self) -> None:
        groups = await self._store.list_groups(only_enabled=True)
        self._cache = {g.chat_id: (g.title, g.topic_hint) for g in groups}
        logger.info("Watched-group cache refreshed: %s groups", len(self._cache))


async def _classify_and_store(
    store: MessageStore,
    local_id: int,
    text: str,
    topic_hint: str,
    sem: asyncio.Semaphore,
) -> None:
    async with sem:
        try:
            verdict = await judge_group(text, topic_hint)
            await store.update_relevance(
                local_id, verdict.relevant, verdict.topic, verdict.summary
            )
            logger.info(
                "Classified local_id=%s relevant=%s topic=%r",
                local_id, verdict.relevant, verdict.topic,
            )
        except Exception:
            logger.exception("realtime classify failed local_id=%s", local_id)


async def _on_group_message(
    event: events.NewMessage.Event,
    store: MessageStore,
    cache: _WatchedGroupCache,
    sem: asyncio.Semaphore,
    *,
    realtime_ai: bool,
    min_text_len: int,
) -> None:
    msg: Message = event.message
    if msg is None or event.is_private:
        return
    chat_id = event.chat_id
    if chat_id is None:
        return
    meta = await cache.get(chat_id)
    if meta is None:
        return
    title, topic_hint = meta
    text = (msg.text or msg.message or "").strip()
    ts = int(msg.date.timestamp()) if msg.date else 0

    row = MessageRow(
        tg_msg_id=msg.id,
        chat_id=chat_id,
        chat_type="group",
        sender_id=getattr(msg, "sender_id", None),
        sender_name=sender_display_name(msg),
        text=text or None,
        media_kind=detect_media_kind(msg),
        ts=ts,
    )
    local_id = await store.upsert_message(row)
    logger.info(
        "Stored realtime msg local_id=%s chat=%r len=%s",
        local_id, title, len(text),
    )

    if not realtime_ai or not text or len(text) < min_text_len:
        return
    asyncio.create_task(
        _classify_and_store(store, local_id, text, topic_hint or "", sem),
        name=f"classify-{local_id}",
    )


def register_group_handler(
    client: TelegramClient,
    store: MessageStore,
    sem: asyncio.Semaphore,
    *,
    realtime_ai: bool,
    min_text_len: int,
) -> _WatchedGroupCache:
    cache = _WatchedGroupCache(store)

    @client.on(events.NewMessage(incoming=True))
    async def _incoming(event: events.NewMessage.Event) -> None:
        if event.is_private:
            return
        try:
            await _on_group_message(
                event, store, cache, sem,
                realtime_ai=realtime_ai,
                min_text_len=min_text_len,
            )
        except Exception:
            logger.exception("group handler crashed; event dropped")

    return cache


async def run(settings: Optional[Settings] = None) -> None:
    settings = settings or get_settings()
    store = MessageStore(str(settings.db_absolute_path))
    await store.init_schema()

    sem = asyncio.Semaphore(settings.classify_concurrency)

    client = build_client(settings)
    await client.start(phone=settings.tg_phone)
    me = await client.get_me()
    register_group_handler(
        client, store, sem,
        realtime_ai=settings.realtime_ai_filter,
        min_text_len=settings.min_group_text_len,
    )
    logger.info(
        "Listener up. id=%s realtime_ai=%s. Press Ctrl-C to stop.",
        me.id, settings.realtime_ai_filter,
    )
    await client.run_until_disconnected()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(run())


if __name__ == "__main__":
    main()
