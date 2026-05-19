"""Smoke tests for the FastAPI dashboard — uses an in-memory DB."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dashboard import create_app
from tools.message_store import MessageRow, MessageStore


@pytest.fixture
def settings(tmp_db_path: str) -> Settings:
    return Settings(
        tg_api_id=1, tg_api_hash="x", tg_phone="+1", tg_session_name="t",
        claude_model="claude-haiku-4-5", db_path=tmp_db_path,
        dashboard_host="127.0.0.1", dashboard_port=8000,
        digest_cron_hour=8, local_tz="UTC",
        watched_groups_init="", max_msgs_per_group=10,
        classify_concurrency=1, realtime_ai_filter=False,
        min_group_text_len=10,
    )


@pytest.fixture
async def primed_store(settings: Settings) -> MessageStore:
    store = MessageStore(settings.db_path)
    await store.init_schema()
    await store.upsert_group(
        chat_id=-1001, title="Test Group", topic_hint="ai",
        source_link="@test", enabled=True,
    )
    local_id = await store.upsert_message(MessageRow(
        tg_msg_id=1, chat_id=-1001, chat_type="group",
        sender_id=1, sender_name="Alice", text="something",
        media_kind=None, ts=1_700_000_000,
    ))
    await store.update_relevance(local_id, True, "Hiring", "summary text")
    await store.save_digest("2026-05-18", -1001, [
        {"tg_msg_id": 1, "ts": 1_700_000_000, "sender_name": "Alice",
         "topic": "Hiring", "summary": "summary text",
         "link": "https://t.me/test/1"},
    ])
    return store


def test_healthz(settings: Settings) -> None:
    app = create_app(settings=settings)
    with TestClient(app) as client:
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json() == {"ok": True}


def test_root_redirects_to_feed(settings: Settings) -> None:
    app = create_app(settings=settings)
    with TestClient(app) as client:
        r = client.get("/", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/feed"


def test_feed_renders_when_empty(settings: Settings) -> None:
    app = create_app(settings=settings)
    with TestClient(app) as client:
        r = client.get("/feed")
        assert r.status_code == 200
        assert "Feed" in r.text
        assert "No relevant messages" in r.text


@pytest.mark.asyncio
async def test_feed_shows_relevant_rows(settings: Settings, primed_store) -> None:
    app = create_app(settings=settings)
    with TestClient(app) as client:
        r = client.get("/feed?window=all")
        assert r.status_code == 200
        assert "Test Group" in r.text
        assert "Hiring" in r.text
        assert "Alice" in r.text


@pytest.mark.asyncio
async def test_digest_renders_section(settings: Settings, primed_store) -> None:
    app = create_app(settings=settings)
    with TestClient(app) as client:
        r = client.get("/digest?date=2026-05-18")
        assert r.status_code == 200
        assert "Test Group" in r.text
        assert "summary text" in r.text
