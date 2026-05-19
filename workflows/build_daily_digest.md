# Workflow: Build a daily digest

## Goal

For a given calendar date in `LOCAL_TZ`, produce one `daily_digests` row per
enabled watched group, containing only the messages classified as relevant
in the 24-hour window [00:00, 24:00).

## Inputs

- `date_str` (optional) — `YYYY-MM-DD` in `LOCAL_TZ`. Default: yesterday.
- `only_group` (optional) — restrict to a single `chat_id`.

## Outputs

- One row per group in `daily_digests` (UPSERT on `(date, chat_id)`).
- `groups_watched.last_scanned_at` bumped to `until_ts`.

## Tools to use

| Step | Tool | Function |
|------|------|----------|
| Convert date to UTC window | `app/run_daily_digest.py` | `_window_for_date` |
| List enabled groups | `tools/message_store.py` | `list_groups(only_enabled=True)` |
| Scan one group | `tools/group_scanner.py` | `scan_group` |
| Persist digest | `tools/message_store.py` | `save_digest` |
| Bump scanned timestamp | `tools/message_store.py` | `mark_group_scanned` |

## Steps

1. Resolve `date_str` to a `[since_ts, until_ts)` UTC window via
   `_window_for_date`.
2. Open / reuse a Telethon client and an initialized `MessageStore`.
3. For each enabled group (or just `only_group`):
   - Call `scan_group(client, store, group, since, until)`. This runs the
     full `scan_group_daily` workflow.
   - Serialize the resulting `ScannedItem`s into dicts.
   - `save_digest(date_str, group.chat_id, items)`.
   - `mark_group_scanned(group.chat_id, until_ts)`.
4. Return.

## When to use

- **Cron path.** `app/scheduler.py` schedules
  `run_daily_digest.run()` at `DIGEST_CRON_HOUR` in `LOCAL_TZ`. Default 08:00.
- **Manual rerun.** `python -m app.run_daily_digest --date 2026-05-18`.
- **Rebuild from existing classified messages.** If you only want to roll
  up rows already in the DB (no new Telegram or Claude calls), use
  `python -m app.build_digest_from_db --date 2026-05-18`.

## Edge cases

- **No groups enabled** → log a warning, no-op.
- **Telegram client lock during scheduler firing** — the scheduler reuses
  the supervisor's client. Standalone CLI starts its own.
- **Same date scanned twice** — `daily_digests` UPSERT replaces the prior
  row, which is fine.
