"""Telethon wrapper: client build, history iteration, flood-wait retry.

The session file lives at `data/sessions/<TG_SESSION_NAME>.session`. First
launch requires interactive code entry (see app.setup_session). All subsequent
runs reuse the file silently.

Used by:
    - app.setup_session
    - app.run_listener
    - tools.resolve_groups, tools.group_scanner
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, AsyncIterator, Awaitable, Callable, Optional, TypeVar

from telethon import TelegramClient
from telethon.errors import (
    AuthKeyUnregisteredError,
    FloodWaitError,
    RpcCallFailError,
    UserDeactivatedBanError,
)
from telethon.tl.custom.message import Message

from app.config import Settings
from tools.fs_security import secure_dir, secure_file

if TYPE_CHECKING:
    from tools.message_store import MessageStore

logger = logging.getLogger(__name__)

T = TypeVar("T")


def build_client(settings: Settings) -> TelegramClient:
    """Create a Telethon client backed by a persistent session file.

    Caller must call `await client.start(phone=settings.tg_phone, ...)` once
    interactively, then `await client.connect()` for subsequent runs.
    """
    secure_dir(settings.sessions_dir)
    session_path = str(settings.session_file)
    return TelegramClient(
        session_path,
        api_id=settings.tg_api_id,
        api_hash=settings.tg_api_hash,
    )


def secure_session_files(settings: Settings) -> None:
    """chmod 0600 on every Telethon session file in sessions_dir.

    Telethon creates the .session file lazily during client.start(), so this
    must be called *after* the first successful login. Best-effort; never raises.
    """
    sessions_dir = settings.sessions_dir
    if not sessions_dir.exists():
        return
    for f in sessions_dir.glob("*.session*"):
        secure_file(f)


async def with_flood_retry(
    coro_factory: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 3,
    base_backoff: float = 2.0,
    store: Optional["MessageStore"] = None,
) -> T:
    """Run `coro_factory()` with FloodWait/transient-error retries.

    `coro_factory` must return a fresh coroutine each call (since coroutines
    can only be awaited once).

    Fatal auth errors (UserDeactivatedBanError, AuthKeyUnregisteredError) are
    logged at CRITICAL and re-raised immediately — they must not be retried.
    The `store` arg is accepted for API compatibility but not used.
    """
    del store  # not used in the watcher build
    attempt = 0
    while True:
        try:
            return await coro_factory()
        except (UserDeactivatedBanError, AuthKeyUnregisteredError) as e:
            logger.critical(
                "Fatal Telegram auth error — account banned or session revoked: %s",
                e,
            )
            raise
        except FloodWaitError as e:
            wait = int(e.seconds) + 1
            logger.warning("FloodWaitError: sleeping %ss (attempt %s)", wait, attempt + 1)
            await asyncio.sleep(wait)
        except RpcCallFailError as e:
            attempt += 1
            if attempt > max_retries:
                logger.error("RpcCallFailError exhausted retries: %s", e)
                raise
            backoff = base_backoff * (2 ** (attempt - 1))
            logger.warning("RpcCallFailError, backing off %.1fs: %s", backoff, e)
            await asyncio.sleep(backoff)


async def iter_history(
    client: TelegramClient,
    chat_id: int,
    since_ts: int,
    until_ts: int,
    max_messages: int = 500,
) -> AsyncIterator[Message]:
    """Yield messages in chronological order whose ts is in [since_ts, until_ts).

    Iterates Telethon's history backwards from `until_ts`, then reverses
    chunks in memory. Bounded by `max_messages` to avoid hammering big groups.
    """
    until_dt = datetime.fromtimestamp(until_ts, tz=timezone.utc)
    collected: list[Message] = []
    async for msg in client.iter_messages(chat_id, offset_date=until_dt, limit=max_messages):
        if msg.date is None:
            continue
        ts = int(msg.date.timestamp())
        if ts < since_ts:
            break
        if ts >= until_ts:
            continue
        collected.append(msg)
    for msg in reversed(collected):
        yield msg


def format_msg_link(chat_id: int, msg_id: int, username: Optional[str] = None) -> str:
    """Build a public t.me/<username>/<msg_id> link when known, else t.me/c form.

    The c/<internal_id> form only opens for users already in the (private)
    supergroup. Public groups should use the username form so anyone can open.
    """
    if username:
        return f"https://t.me/{username.lstrip('@')}/{msg_id}"
    cid = str(chat_id)
    if cid.startswith("-100"):
        cid = cid[4:]
    return f"https://t.me/c/{cid}/{msg_id}"


def detect_media_kind(msg: Message) -> Optional[str]:
    if msg.photo is not None:
        return "photo"
    if msg.voice is not None:
        return "voice"
    if msg.video is not None:
        return "video"
    if msg.audio is not None:
        return "audio"
    if msg.sticker is not None:
        return "sticker"
    if msg.document is not None:
        return "document"
    return None


def sender_display_name(msg: Message) -> Optional[str]:
    sender = msg.sender
    if sender is None:
        return None
    parts: list[str] = []
    first = getattr(sender, "first_name", None)
    last = getattr(sender, "last_name", None)
    username = getattr(sender, "username", None)
    if first:
        parts.append(first)
    if last:
        parts.append(last)
    if parts:
        return " ".join(parts)
    if username:
        return f"@{username}"
    title = getattr(sender, "title", None)
    return title
