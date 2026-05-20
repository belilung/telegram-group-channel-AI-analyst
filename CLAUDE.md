# Claude Code instructions

You're working inside a **Telegram Watcher** project — a 24/7 monitor for
Telegram groups and channels built on the **WAT framework** (Workflows,
Agents, Tools). The whole thing has one job: watch chosen groups, filter
noise via Claude, surface relevant items in a local dashboard plus a daily
digest. No DMs, no leads, no Sheets. Stay focused on this scope.

## First-run onboarding (READ THIS FIRST)

**Before doing anything else, check whether `.env` exists in the project root.**

- **`.env` is missing** → this is a fresh clone. Do NOT write code, do NOT
  suggest changes. Instead, open [`workflows/onboarding.md`](workflows/onboarding.md)
  (or [`workflows/onboarding.ru.md`](workflows/onboarding.ru.md) if the user
  is writing to you in Russian) and walk the user through it **step by step**,
  asking the questions in order, running the commands on their behalf, and
  confirming each checkpoint before moving on. The user is likely a first-time
  Claude Code user — assume zero prior knowledge of Python, Telegram MTProto,
  or virtualenvs. Greet them and start step 1.
- **`.env` exists** → setup is already done. Behave normally: implement,
  refactor, debug, etc., per the rest of this file.

**Sensitive data handling during onboarding:**
- After the user gives you their `TG_API_HASH`, `TG_PHONE`, or 2FA password,
  write them into the appropriate file (`.env` or the temp-file stdin
  mechanism in `app/setup_session.py`) and **never echo them back into the
  chat transcript**. If you must confirm a value, show only its first 4
  characters and length: `"api_hash starts with 'cd06' (32 chars total) ✓"`.
- Never `echo "<password>" | python -m app.setup_session`. The 2FA password
  flow uses a temp-file callback — use that path.

**Doc-update rule:** when you change any of `README.md`, `INSTALL.md`,
`workflows/onboarding.md`, update the matching `.ru.md` mirror in the same
commit. The bilingual docs are mandatory, not optional.

## The WAT layers

**Workflows (`workflows/`)** — markdown SOPs. They describe the end-to-end
task: inputs, which tools to call, expected outputs, edge cases. Treat them
as authoritative. Don't silently invent a new workflow — update the existing
one if behaviour needs to change.

**Agent (you, or the runtime Claude in `tools/classifier.py`)** — picks the
right workflow, executes tools in order, handles failures, asks the user when
unclear. Don't try to reinvent execution logic — call existing tools.

**Tools (`tools/`)** — deterministic Python. Each module does one thing:
- `telegram_client.py` — Telethon wrapper, flood-wait retry, history
  iteration.
- `claude_chat.py` — subprocess wrapper around the `claude` CLI.
- `classifier.py` — single LLM call: `judge_group(text, topic_hint)`.
- `message_store.py` — SQLite repo, 3 tables only (`messages`,
  `groups_watched`, `daily_digests`).
- `group_scanner.py` — `scan_group(client, store, group, since, until)`.
- `resolve_groups.py` — turn `@username` / t.me/c links into chat_ids.

## How to operate

1. **Look for an existing tool before adding code.** The whole point of WAT
   is that tools stay deterministic and reusable. If something is missing,
   add a single-purpose tool; don't extend an existing one beyond its name.

2. **Don't mutate.** SQLite rows are written through `upsert_*` and
   `update_*` methods that return new rows. Dataclasses are `frozen=True`.

3. **Errors are signals, not noise.** When a Telethon call fails with
   `FloodWaitError`, the wrapper sleeps and retries. When Claude returns
   non-JSON, the classifier retries once with a strict suffix, then fails
   closed (returns `relevant: false`). Don't add try/except that just
   swallows.

4. **The system prompt for relevance is one file.** It lives at
   `system_prompts/group_relevance_filter.md`. Students will edit it to fit
   their niche. Don't duplicate that prompt anywhere else.

5. **The single entrypoint is `app/supervisor.py`.** It runs the listener,
   scheduler and dashboard in one event loop. Don't add another long-running
   process — extend the supervisor.

## File layout

```
app/
  supervisor.py        ← single 24/7 entrypoint
  setup_session.py     ← one-shot Telegram login
  run_listener.py      ← realtime group handler
  run_daily_digest.py  ← cron + manual CLI
  build_digest_from_db.py
  scheduler.py         ← APScheduler glue
  dashboard.py         ← FastAPI + Jinja2
  config.py            ← pydantic-settings
  templates/  static/  ← UI
tools/
  telegram_client.py   claude_chat.py
  classifier.py        message_store.py
  group_scanner.py     resolve_groups.py
system_prompts/
  group_relevance_filter.md  ← the only AI prompt
workflows/
  scan_group_daily.md
  build_daily_digest.md
tests/                 ← pytest
```

## Things this project does NOT do (don't add them on a whim)

- No DM classification.
- No lead scoring / aggregation / Sheets export.
- No `python-telegram-bot` (Bot API). It's a user account via MTProto.
- No voice transcription.
- No Anthropic API key — only the `claude` CLI.

If a request crosses one of these lines, push back: either confirm with the
user that they really want to expand scope, or hand them a small, separate
follow-up project.

## Self-improvement loop

When you hit something that breaks repeatedly:
1. Identify the root cause.
2. Fix the tool, not the workflow first.
3. Verify the fix.
4. Update the workflow (or this CLAUDE.md) to capture the lesson.

That's how the framework gets smarter over time.
