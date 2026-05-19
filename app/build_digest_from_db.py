"""Build daily_digests rows from already-classified group messages already in
the database. Uses ZERO Claude or Telegram calls — pure SQL.

Use this when a scan was interrupted (messages got relevance verdicts but the
final `save_digest` call never fired), or when you want to retroactively
construct digests for any date with existing data.

Run:
    python -m app.build_digest_from_db --date 2026-05-13
    python -m app.build_digest_from_db --date 2026-05-13 --group <chat_id>
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Optional

from app.config import Settings, get_settings
from app.run_daily_digest import _window_for_date
from tools.message_store import MessageStore
from tools.telegram_client import format_msg_link

logger = logging.getLogger(__name__)


async def _build_for_group(
    store: MessageStore,
    date_str: str,
    chat_id: int,
    since_ts: int,
    until_ts: int,
) -> int:
    """Read relevant rows from messages, write into daily_digests.

    Returns the number of items written.
    """
    async with store._conn() as conn:  # noqa: SLF001
        cur = await conn.execute(
            """
            SELECT tg_msg_id, ts, sender_name, topic, summary
              FROM messages
             WHERE chat_id = ?
               AND chat_type = 'group'
               AND relevant = 1
               AND ts >= ?
               AND ts < ?
             ORDER BY ts ASC
            """,
            (chat_id, since_ts, until_ts),
        )
        rows = await cur.fetchall()

    items: list[dict] = []
    for r in rows:
        items.append({
            "tg_msg_id": r["tg_msg_id"],
            "ts": r["ts"],
            "sender_name": r["sender_name"],
            "topic": r["topic"],
            "summary": r["summary"],
            "link": format_msg_link(chat_id, r["tg_msg_id"]),
        })
    await store.save_digest(date_str, chat_id, items)
    await store.mark_group_scanned(chat_id, until_ts)
    return len(items)


async def _run(args: argparse.Namespace, settings: Settings) -> int:
    store = MessageStore(str(settings.db_absolute_path))
    await store.init_schema()

    since_ts, until_ts = _window_for_date(args.date, settings.local_tz)
    logger.info("Window: %s (since=%s until=%s)", args.date, since_ts, until_ts)

    groups = await store.list_groups(only_enabled=True)
    if args.group is not None:
        groups = [g for g in groups if g.chat_id == args.group]
    if not groups:
        logger.warning("No enabled groups in DB — nothing to do.")
        return 0

    total = 0
    for group in groups:
        n = await _build_for_group(store, args.date, group.chat_id, since_ts, until_ts)
        total += n
        logger.info("digest date=%s chat_id=%s title=%r items=%s",
                    args.date, group.chat_id, group.title, n)

    print(f"Built {len(groups)} digest row(s) for {args.date}; {total} items total.")
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Rebuild daily_digests from existing classified group messages.")
    p.add_argument("--date", required=True, help="YYYY-MM-DD (LOCAL_TZ)")
    p.add_argument("--group", type=int, default=None,
                   help="Restrict to a single chat_id.")
    return p.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    raise SystemExit(asyncio.run(_run(_parse_args(), get_settings())))


if __name__ == "__main__":
    main()
