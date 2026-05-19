# Workflow: Scan a watched group for one [since_ts, until_ts) window

## Goal

For each enabled group in `groups_watched`, pull all messages whose timestamp
falls in `[since_ts, until_ts)`, persist them, classify each via Claude
against the group's `topic_hint`, and return the items that came back
`relevant=true`.

## Inputs

- `client` — an authenticated `telethon.TelegramClient`.
- `store` — a connected `tools.message_store.MessageStore`.
- `group` — a `GroupRow` (chat_id, title, topic_hint, source_link).
- `since_ts`, `until_ts` — UNIX seconds, half-open window.

## Outputs

- A list of `ScannedItem` (tg_msg_id, ts, sender_name, topic, summary, link)
  for messages classified as relevant.
- Side effect: every fetched message is upserted into `messages` with
  `relevant=0|1`, `topic`, `summary`, `processed_at`.

## Tools to use

| Step | Tool | Function |
|------|------|----------|
| Iterate history with flood-wait retry | `tools/telegram_client.py` | `iter_history`, `with_flood_retry` |
| Upsert each message | `tools/message_store.py` | `upsert_message`, `update_relevance` |
| Skip already-classified messages | `tools/message_store.py` | `get_message_relevance` |
| Classify relevance | `tools/classifier.py` | `judge_group(text, topic_hint)` |
| Build message link | `tools/telegram_client.py` | `format_msg_link` |

## Steps

1. Open an async generator over Telethon history, bounded to
   `MAX_MSGS_PER_GROUP`.
2. For every message:
   - Skip if `msg.out` (you sent it) or sender is a bot.
   - Extract text or caption. Persist via `upsert_message`.
   - If the row already has a `relevant` verdict from a prior run, re-use it.
     Don't call Claude again.
   - If text is shorter than `MIN_GROUP_TEXT_LEN`, mark `relevant=False` and
     skip the LLM call.
   - Otherwise, queue an async `judge_group` call (bounded by a semaphore of
     size `CLASSIFY_CONCURRENCY`). On result, `update_relevance` and add a
     `ScannedItem` to the output list if relevant.
3. Sort results by ts ascending. Return.

## Edge cases

- **Telegram flood-wait** — `with_flood_retry` handles it: sleeps and retries.
- **Claude returns garbage** — `judge_group` retries once with a strict
  suffix, then fails closed (`relevant=False`). Don't escalate to the caller.
- **Same message scanned twice** — the `(chat_id, tg_msg_id)` UNIQUE
  constraint keeps it idempotent; the existing relevance verdict is reused.
- **Empty / sticker / media-only** — no text means no LLM call; row still
  persists with `relevant=False`.

## Used by

- `app/run_daily_digest.py` (cron entrypoint).
- `app/supervisor.py` (history catch-up at startup — bounded window).
