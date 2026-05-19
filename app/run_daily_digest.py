"""Daily digest builder.

Computes the previous-day window in LOCAL_TZ (or a custom --date) and scans
every enabled watched group, then writes one row per group into daily_digests.

Run manually:
    python -m app.run_daily_digest                      # yesterday in LOCAL_TZ
    python -m app.run_daily_digest --date 2026-05-14
    python -m app.run_daily_digest --group -1001234567

Used by app.scheduler at DIGEST_CRON_HOUR.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from dateutil import tz
from telethon import TelegramClient

from app.config import Settings, get_settings
from tools.group_scanner import scan_group
from tools.message_store import MessageStore
from tools.telegram_client import build_client

logger = logging.getLogger(__name__)


def _window_for_date(date_str: str, local_tz_name: str) -> tuple[int, int]:
    """Convert a YYYY-MM-DD local-TZ date to a [since_ts, until_ts) UTC window."""
    local = tz.gettz(local_tz_name)
    if local is None:
        raise ValueError(f"Unknown timezone: {local_tz_name!r}")
    d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=local)
    start = d.astimezone(timezone.utc)
    end = (d + timedelta(days=1)).astimezone(timezone.utc)
    return int(start.timestamp()), int(end.timestamp())


def _yesterday_str(local_tz_name: str) -> str:
    local = tz.gettz(local_tz_name)
    today = datetime.now(local).date()
    return (today - timedelta(days=1)).isoformat()


async def run(
    date_str: Optional[str] = None,
    only_group: Optional[int] = None,
    settings: Optional[Settings] = None,
    external_client: Optional[TelegramClient] = None,
) -> None:
    settings = settings or get_settings()
    date_str = date_str or _yesterday_str(settings.local_tz)
    since_ts, until_ts = _window_for_date(date_str, settings.local_tz)

    store = MessageStore(str(settings.db_absolute_path))
    await store.init_schema()

    client = external_client or build_client(settings)
    if external_client is None:
        await client.start(phone=settings.tg_phone)

    groups = await store.list_groups(only_enabled=True)
    if only_group is not None:
        groups = [g for g in groups if g.chat_id == only_group]
    if not groups:
        logger.warning("No enabled groups found — nothing to digest.")
        if external_client is None:
            await client.disconnect()
        return

    logger.info("Building digest for %s — %s groups", date_str, len(groups))
    for group in groups:
        try:
            items = await scan_group(client, store, group, since_ts, until_ts)
        except Exception:
            logger.exception("scan_group failed for chat_id=%s title=%r",
                             group.chat_id, group.title)
            continue
        items_dicts = [asdict(item) for item in items]
        await store.save_digest(date_str, group.chat_id, items_dicts)
        await store.mark_group_scanned(group.chat_id, until_ts)
        logger.info(
            "Digest saved: date=%s chat_id=%s title=%r relevant=%s",
            date_str, group.chat_id, group.title, len(items_dicts),
        )

    if external_client is None:
        await client.disconnect()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build daily Telegram group digest.")
    parser.add_argument("--date", type=str, default=None,
                        help="YYYY-MM-DD in LOCAL_TZ. Default: yesterday.")
    parser.add_argument("--group", type=int, default=None,
                        help="Restrict to a single chat_id.")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = _parse_args()
    asyncio.run(run(date_str=args.date, only_group=args.group))


if __name__ == "__main__":
    main()
