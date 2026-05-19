"""Resolve Telegram group references (links, @usernames, private invite codes)
into concrete chat_ids and persist them into the `groups_watched` table.

Input format for `WATCHED_GROUPS_INIT`:
    "<ref>|<topic_hint>;<ref>|<topic_hint>;..."

`<ref>` is one of:
    - @username
    - https://t.me/<username>
    - https://t.me/c/<internal_id>/<msg_id>   (private supergroup — user must be a member)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, PeerChannel

from tools.message_store import MessageStore
from tools.telegram_client import with_flood_retry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolveSpec:
    raw: str
    topic_hint: str


@dataclass(frozen=True)
class GroupResolved:
    chat_id: int
    title: str
    topic_hint: str
    source_link: str


_PRIVATE_LINK = re.compile(r"https?://t\.me/c/(\d+)(?:/\d+)?/?")
_PUBLIC_LINK = re.compile(r"https?://t\.me/([A-Za-z0-9_]+)(?:/\d+)?/?")
_USERNAME = re.compile(r"^@([A-Za-z0-9_]+)$")


def parse_init_string(init: str) -> list[ResolveSpec]:
    """Parse `link|hint;link|hint;...` into specs. Ignores empty fragments."""
    out: list[ResolveSpec] = []
    for chunk in init.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "|" in chunk:
            raw, hint = (s.strip() for s in chunk.split("|", 1))
        else:
            raw, hint = chunk, ""
        if raw:
            out.append(ResolveSpec(raw=raw, topic_hint=hint))
    return out


async def _resolve_one(client: TelegramClient, spec: ResolveSpec) -> Optional[GroupResolved]:
    raw = spec.raw

    private_m = _PRIVATE_LINK.match(raw)
    if private_m:
        internal_id = int(private_m.group(1))
        # Telethon needs the -100<id> form for channel peers
        peer = PeerChannel(channel_id=internal_id)
        entity = await with_flood_retry(lambda: client.get_entity(peer))
    else:
        user_m = _USERNAME.match(raw)
        if user_m:
            handle = user_m.group(1)
        else:
            pub_m = _PUBLIC_LINK.match(raw)
            if not pub_m:
                logger.warning("Could not parse group ref: %s", raw)
                return None
            handle = pub_m.group(1)
        entity = await with_flood_retry(lambda: client.get_entity(handle))

    if not isinstance(entity, (Channel, Chat)):
        logger.warning("Resolved entity is not a chat/channel: %r", entity)
        return None

    chat_id_raw = entity.id
    # Telethon returns positive channel ids; SQLite stores -100<id> canonical form
    if isinstance(entity, Channel):
        chat_id = int(f"-100{chat_id_raw}")
    else:
        chat_id = -int(chat_id_raw)

    title = getattr(entity, "title", None) or raw
    return GroupResolved(
        chat_id=chat_id,
        title=title,
        topic_hint=spec.topic_hint,
        source_link=raw,
    )


async def resolve_and_persist(
    client: TelegramClient, store: MessageStore, init_string: str
) -> list[GroupResolved]:
    """Resolve all specs from `init_string` and upsert them into groups_watched.

    Failures are logged and skipped — caller can re-run later for missing ones.
    """
    specs = parse_init_string(init_string)
    resolved: list[GroupResolved] = []
    for spec in specs:
        try:
            res = await _resolve_one(client, spec)
        except Exception as exc:
            logger.error("Resolve failed for %s: %s", spec.raw, exc)
            continue
        if res is None:
            continue
        await store.upsert_group(
            chat_id=res.chat_id,
            title=res.title,
            topic_hint=res.topic_hint or None,
            source_link=res.source_link,
            enabled=True,
        )
        resolved.append(res)
        logger.info(
            "Resolved %s -> chat_id=%s title=%r topic=%s",
            spec.raw,
            res.chat_id,
            res.title,
            res.topic_hint,
        )
    return resolved
