"""APScheduler wiring — only the daily group digest job."""

from __future__ import annotations

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telethon import TelegramClient

from app.config import Settings
from app.run_daily_digest import run as run_daily_digest
from tools.message_store import MessageStore

logger = logging.getLogger(__name__)


def build_scheduler(
    settings: Settings,
    client: TelegramClient,
    store: Optional[MessageStore] = None,
) -> AsyncIOScheduler:
    del store  # not needed; run_daily_digest opens its own store
    scheduler = AsyncIOScheduler(timezone=settings.local_tz)

    async def _daily_digest_job() -> None:
        try:
            logger.info("daily_digest cron firing")
            await run_daily_digest(settings=settings, external_client=client)
        except Exception:
            logger.exception("daily_digest job failed")

    scheduler.add_job(
        _daily_digest_job,
        trigger=CronTrigger(hour=settings.digest_cron_hour, minute=0),
        id="daily_digest",
        replace_existing=True,
        misfire_grace_time=60 * 60,
    )
    return scheduler
