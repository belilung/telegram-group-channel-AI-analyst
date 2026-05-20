"""Dashboard Bearer-token guard and security headers."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dashboard import create_app


def _settings(tmp_db_path: str, *, token: str = "", host: str = "127.0.0.1") -> Settings:
    return Settings(
        tg_api_id=1, tg_api_hash="x" * 32, tg_phone="+1", tg_session_name="t",
        claude_model="claude-haiku-4-5", db_path=tmp_db_path,
        dashboard_host=host, dashboard_port=8000, dashboard_token=token,
        digest_cron_hour=8, local_tz="UTC",
        watched_groups_init="", max_msgs_per_group=10,
        classify_concurrency=1, realtime_ai_filter=False,
        min_group_text_len=10,
    )


def test_no_token_means_open_dashboard(tmp_db_path: str) -> None:
    app = create_app(settings=_settings(tmp_db_path))
    with TestClient(app) as client:
        assert client.get("/feed").status_code == 200


def test_token_required_when_set(tmp_db_path: str) -> None:
    token = "k" * 64
    app = create_app(settings=_settings(tmp_db_path, token=token))
    with TestClient(app) as client:
        assert client.get("/feed").status_code == 401
        assert client.get(
            "/feed", headers={"Authorization": f"Bearer {token}"}
        ).status_code == 200
        assert client.get(
            "/feed", headers={"Authorization": "Bearer wrong"}
        ).status_code == 401


def test_healthz_always_open(tmp_db_path: str) -> None:
    app = create_app(settings=_settings(tmp_db_path, token="t" * 64))
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200


def test_security_headers_present(tmp_db_path: str) -> None:
    app = create_app(settings=_settings(tmp_db_path))
    with TestClient(app) as client:
        r = client.get("/feed")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "no-referrer"
