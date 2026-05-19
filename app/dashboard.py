"""FastAPI + Jinja2 dashboard for the Telegram Watcher.

Routes:
    GET /                  → redirect to /feed
    GET /healthz           → liveness probe
    GET /feed              → recent relevant messages from watched groups
    GET /digest            → daily group digests (by date)
    GET /digest/window     → date picker for /digest
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncIterator, Optional

from dateutil import tz
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import Settings, get_settings
from tools.message_store import MessageStore

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "app" / "templates"
STATIC_DIR = PROJECT_ROOT / "app" / "static"


def _fmt_ts(ts: int, tz_name: str) -> str:
    if not ts:
        return ""
    local = tz.gettz(tz_name) or tz.tzutc()
    return datetime.fromtimestamp(ts, tz=local).strftime("%Y-%m-%d %H:%M")


def _window_seconds(window: str) -> Optional[int]:
    """Return window length in seconds. None for 'all'."""
    if window == "all":
        return None
    if window.endswith("d"):
        try:
            return int(window[:-1]) * 86400
        except ValueError:
            pass
    if window.endswith("h"):
        try:
            return int(window[:-1]) * 3600
        except ValueError:
            pass
    return 2 * 86400


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()
    store = MessageStore(str(settings.db_absolute_path))

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["fmt_ts"] = lambda ts, tz_name=settings.local_tz: _fmt_ts(ts, tz_name)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await store.init_schema()
        yield

    app = FastAPI(title="Telegram Watcher", lifespan=lifespan)
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse("/feed", status_code=302)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict:
        return {"ok": True}

    @app.get("/feed", response_class=HTMLResponse)
    async def feed(
        request: Request,
        window: str = Query("2d"),
        chat_id: Optional[int] = Query(None),
    ) -> HTMLResponse:
        now = int(datetime.now(tz=timezone.utc).timestamp())
        secs = _window_seconds(window)
        since_ts = now - secs if secs is not None else 0
        until_ts = now + 1
        rows = await store.list_relevant_messages(
            since_ts=since_ts, until_ts=until_ts, chat_id=chat_id, limit=500,
        )
        groups = await store.list_groups(only_enabled=False)
        groups_by_id = {g.chat_id: g for g in groups}
        items = [
            {
                "msg": m,
                "group": groups_by_id.get(m.chat_id),
            }
            for m in rows
        ]
        template = env.get_template("feed.html")
        html = template.render(
            items=items,
            groups=groups,
            window=window,
            active_chat_id=chat_id,
            local_tz=settings.local_tz,
            current_path="/feed",
        )
        return HTMLResponse(html)

    @app.get("/digest", response_class=HTMLResponse)
    async def digest(
        request: Request,
        date: Optional[str] = Query(None),
    ) -> HTMLResponse:
        all_dates = await store.list_digest_dates(limit=60)
        selected = date or (all_dates[0] if all_dates else "")
        groups = await store.list_groups(only_enabled=False)
        groups_by_id = {g.chat_id: g for g in groups}
        sections: list[dict] = []
        if selected:
            for g in groups:
                items = await store.get_digest(selected, g.chat_id)
                if items is None:
                    continue
                sections.append({"group": g, "entries": items})
        template = env.get_template("digest.html")
        html = template.render(
            selected=selected,
            dates=all_dates,
            sections=sections,
            local_tz=settings.local_tz,
            current_path="/digest",
        )
        return HTMLResponse(html)

    @app.get("/digest/window", response_class=HTMLResponse)
    async def digest_window(
        request: Request,
        window: str = Query("7d"),
    ) -> HTMLResponse:
        # Pick all dates that fall inside the window, then list per-day digests.
        secs = _window_seconds(window) or 30 * 86400
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(seconds=secs)).date().isoformat()
        all_dates = await store.list_digest_dates(limit=60)
        dates_in_window = [d for d in all_dates if d >= cutoff]
        groups = await store.list_groups(only_enabled=False)
        groups_by_id = {g.chat_id: g for g in groups}
        days: list[dict] = []
        for d in dates_in_window:
            day_sections: list[dict] = []
            for g in groups:
                items = await store.get_digest(d, g.chat_id)
                if items is None:
                    continue
                day_sections.append({"group": g, "entries": items})
            if day_sections:
                days.append({"date": d, "sections": day_sections})
        template = env.get_template("digest_window.html")
        html = template.render(
            window=window,
            days=days,
            local_tz=settings.local_tz,
            current_path="/digest/window",
        )
        return HTMLResponse(html)

    return app
