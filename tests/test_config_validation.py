"""Settings.validate_runtime — catches missing/invalid secrets early."""

from __future__ import annotations

import pytest

from app.config import Settings


def _base_kwargs(**overrides) -> dict:
    base = dict(
        tg_api_id=12345,
        tg_api_hash="a" * 32,
        tg_phone="+380501234567",
        tg_session_name="t",
        claude_model="claude-haiku-4-5",
        db_path="data/x.db",
        dashboard_host="127.0.0.1",
        dashboard_port=8000,
        digest_cron_hour=8,
        local_tz="UTC",
        watched_groups_init="",
        max_msgs_per_group=10,
        classify_concurrency=1,
        realtime_ai_filter=False,
        min_group_text_len=10,
    )
    base.update(overrides)
    return base


def test_valid_settings_pass() -> None:
    Settings(**_base_kwargs()).validate_runtime()


@pytest.mark.parametrize(
    "field,bad_value,needle",
    [
        ("tg_api_id", 0, "TG_API_ID"),
        ("tg_api_hash", "", "TG_API_HASH"),
        ("tg_api_hash", "tooshort", "TG_API_HASH"),
        ("tg_phone", "", "TG_PHONE"),
        ("tg_phone", "380501234567", "TG_PHONE"),  # missing leading +
    ],
)
def test_missing_or_invalid_fields_raise(field, bad_value, needle) -> None:
    settings = Settings(**_base_kwargs(**{field: bad_value}))
    with pytest.raises(RuntimeError, match=needle):
        settings.validate_runtime()


def test_multiple_problems_all_reported() -> None:
    settings = Settings(**_base_kwargs(tg_api_id=0, tg_api_hash="", tg_phone=""))
    with pytest.raises(RuntimeError) as exc:
        settings.validate_runtime()
    msg = str(exc.value)
    assert "TG_API_ID" in msg
    assert "TG_API_HASH" in msg
    assert "TG_PHONE" in msg
