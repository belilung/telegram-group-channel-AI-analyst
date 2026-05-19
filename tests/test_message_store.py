"""Unit tests for MessageStore — covers the 3-table schema."""

from __future__ import annotations

import pytest

from tools.message_store import MessageRow, MessageStore


@pytest.mark.asyncio
async def test_init_schema_idempotent(tmp_db_path: str) -> None:
    store = MessageStore(tmp_db_path)
    await store.init_schema()
    await store.init_schema()  # second call must not raise


@pytest.mark.asyncio
async def test_upsert_and_relevance(tmp_db_path: str) -> None:
    store = MessageStore(tmp_db_path)
    await store.init_schema()

    row = MessageRow(
        tg_msg_id=100, chat_id=-1001, chat_type="group",
        sender_id=42, sender_name="Alice",
        text="hello world", media_kind=None, ts=1_700_000_000,
    )
    local_id = await store.upsert_message(row)
    assert isinstance(local_id, int) and local_id > 0

    # Upserting the same (chat_id, tg_msg_id) returns the same local_id
    local_id2 = await store.upsert_message(row)
    assert local_id == local_id2

    # Relevance starts unset
    assert await store.get_message_relevance(-1001, 100) is None

    await store.update_relevance(local_id, True, "Hiring", "Sample summary")
    assert await store.get_message_relevance(-1001, 100) == 1

    await store.update_relevance(local_id, False, None, None)
    assert await store.get_message_relevance(-1001, 100) == 0


@pytest.mark.asyncio
async def test_groups_crud(tmp_db_path: str) -> None:
    store = MessageStore(tmp_db_path)
    await store.init_schema()

    await store.upsert_group(
        chat_id=-1001, title="Group A", topic_hint="ai",
        source_link="@group_a", enabled=True,
    )
    await store.upsert_group(
        chat_id=-1002, title="Group B", topic_hint="3d",
        source_link="@group_b", enabled=False,
    )

    enabled = await store.list_groups(only_enabled=True)
    assert [g.chat_id for g in enabled] == [-1001]

    all_groups = await store.list_groups(only_enabled=False)
    assert {g.chat_id for g in all_groups} == {-1001, -1002}

    g = await store.get_group(-1001)
    assert g is not None and g.title == "Group A" and g.topic_hint == "ai"

    await store.mark_group_scanned(-1001, 1_700_000_000)
    g = await store.get_group(-1001)
    assert g and g.last_scanned_at == 1_700_000_000


@pytest.mark.asyncio
async def test_digest_roundtrip(tmp_db_path: str) -> None:
    store = MessageStore(tmp_db_path)
    await store.init_schema()

    items = [{"tg_msg_id": 1, "ts": 100, "topic": "Hiring", "summary": "x"}]
    await store.save_digest("2026-05-18", -1001, items)

    got = await store.get_digest("2026-05-18", -1001)
    assert got == items

    # Upsert overwrites
    items2 = [{"tg_msg_id": 2, "ts": 200}]
    await store.save_digest("2026-05-18", -1001, items2)
    assert await store.get_digest("2026-05-18", -1001) == items2

    # Date listing
    await store.save_digest("2026-05-19", -1001, [])
    dates = await store.list_digest_dates()
    assert dates[0] == "2026-05-19"
    assert "2026-05-18" in dates


@pytest.mark.asyncio
async def test_list_relevant_messages_window(tmp_db_path: str) -> None:
    store = MessageStore(tmp_db_path)
    await store.init_schema()

    rows = [
        (10, 1000, True),
        (11, 1500, False),
        (12, 2000, True),
        (13, 3000, True),
    ]
    for tg_id, ts, relevant in rows:
        local_id = await store.upsert_message(MessageRow(
            tg_msg_id=tg_id, chat_id=-1001, chat_type="group",
            sender_id=1, sender_name="x", text="t", media_kind=None, ts=ts,
        ))
        await store.update_relevance(local_id, relevant, "topic", "summary")

    out = await store.list_relevant_messages(since_ts=1500, until_ts=2500)
    assert [m.tg_msg_id for m in out] == [12]

    out2 = await store.list_relevant_messages(since_ts=0, until_ts=4000)
    assert {m.tg_msg_id for m in out2} == {10, 12, 13}
