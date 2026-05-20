"""Single entrypoint: listener + scheduler + uvicorn in one asyncio loop.

Run:
    python -m app.supervisor

Combines:
    - Telethon MTProto session (single login)
    - Realtime group/channel listener
    - Daily digest cron at DIGEST_CRON_HOUR
    - FastAPI dashboard on DASHBOARD_PORT
"""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Optional

import uvicorn
from telethon import TelegramClient

from app.config import Settings, get_settings
from app.dashboard import create_app
from app.run_listener import register_group_handler
from app.scheduler import build_scheduler
from tools.message_store import MessageStore
from tools.resolve_groups import resolve_and_persist
from tools.telegram_client import build_client

logger = logging.getLogger(__name__)


async def _wait_for_disconnect(client: TelegramClient) -> None:
    await client.disconnected  # type: ignore[attr-defined]


async def _seed_watched_groups(
    client: TelegramClient, store: MessageStore, settings: Settings
) -> None:
    """If WATCHED_GROUPS_INIT is set and DB has no groups yet, resolve them."""
    existing = await store.list_groups(only_enabled=False)
    if existing:
        return
    init = (settings.watched_groups_init or "").strip()
    if not init:
        return
    try:
        resolved = await resolve_and_persist(client, store, init)
        logger.info("Seeded watched groups from WATCHED_GROUPS_INIT: %s", len(resolved))
    except Exception:
        logger.exception("Failed to seed watched groups; continuing")


_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _enforce_dashboard_guard(settings: Settings) -> None:
    """If dashboard binds outside loopback, require a Bearer token."""
    if settings.dashboard_host in _LOCAL_HOSTS:
        return
    if not settings.dashboard_token:
        raise RuntimeError(
            f"DASHBOARD_HOST is set to '{settings.dashboard_host}' (non-loopback). "
            "This exposes the dashboard to the network without authentication. "
            "Either set DASHBOARD_HOST=127.0.0.1 or set DASHBOARD_TOKEN in .env "
            "to a strong random string (e.g. `openssl rand -hex 32`)."
        )
    logger.warning(
        "Dashboard exposed on %s:%s — Bearer token required on /feed and /digest",
        settings.dashboard_host, settings.dashboard_port,
    )


async def supervise(settings: Optional[Settings] = None) -> None:
    settings = settings or get_settings()
    settings.validate_runtime()
    _enforce_dashboard_guard(settings)

    store = MessageStore(str(settings.db_absolute_path))
    await store.init_schema()

    sem = asyncio.Semaphore(settings.classify_concurrency)

    client = build_client(settings)
    await client.start(phone=settings.tg_phone)
    me = await client.get_me()
    logger.info(
        "Supervisor: logged in id=%s username=@%s realtime_ai=%s",
        me.id, getattr(me, "username", None), settings.realtime_ai_filter,
    )

    await _seed_watched_groups(client, store, settings)

    register_group_handler(
        client, store, sem,
        realtime_ai=settings.realtime_ai_filter,
        min_text_len=settings.min_group_text_len,
    )
    logger.info("Realtime group handler armed")

    try:
        await client.catch_up()
        logger.info("catch_up() done — replayed missed updates")
    except Exception:
        logger.exception("catch_up() failed (non-fatal)")

    scheduler = build_scheduler(settings, client, store=store)
    scheduler.start()
    logger.info(
        "Scheduler armed: daily_digest at %02d:00 %s",
        settings.digest_cron_hour, settings.local_tz,
    )

    app = create_app(settings=settings)
    config = uvicorn.Config(
        app,
        host=settings.dashboard_host,
        port=settings.dashboard_port,
        log_level="info",
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    stop_event = asyncio.Event()

    def _request_stop(*_: object) -> None:
        logger.info("Stop signal received; shutting down supervisor")
        stop_event.set()
        server.should_exit = True

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            signal.signal(sig, lambda *_: _request_stop())

    serve_task = asyncio.create_task(server.serve(), name="uvicorn.serve")
    listener_task = asyncio.create_task(_wait_for_disconnect(client), name="listener")

    logger.info(
        "Dashboard at http://%s:%s  (Ctrl-C to stop)",
        settings.dashboard_host, settings.dashboard_port,
    )

    done, pending = await asyncio.wait(
        {serve_task, listener_task, asyncio.create_task(stop_event.wait())},
        return_when=asyncio.FIRST_COMPLETED,
    )

    server.should_exit = True
    for t in pending:
        t.cancel()
    scheduler.shutdown(wait=False)
    if client.is_connected():
        await client.disconnect()
    for t in done | pending:
        try:
            await t
        except (asyncio.CancelledError, Exception):
            pass


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(supervise())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
