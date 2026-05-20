# Telegram Group/Channel AI Analyst

> 🌐 **[English](README.md)** | **[Русский](README.ru.md)**

24/7 watcher for Telegram groups and channels. Connects to Telegram as a
**user account** via MTProto (not as a bot), listens to messages in the groups
and channels you choose, runs each message through Claude to filter out the
noise, and surfaces only the relevant items in a local web dashboard plus a
daily digest.

Built on the **WAT framework** (Workflows, Agents, Tools): deterministic
Python tools do the work, AI handles the decisions, markdown workflows
document each end-to-end task.

---

## Quick start (with Claude Code)

If you're new to Telegram MTProto, Python virtualenvs, or even Claude Code
itself — **don't read the docs first**. Just do this:

```bash
git clone https://github.com/belilung/telegram-group-channel-AI-analyst.git TelegramWatcher
cd TelegramWatcher
claude
```

Then say to Claude:

> **"help me set this up"**

Claude will walk you through every step: getting Telegram API credentials,
writing `.env`, creating a virtual environment, picking the groups and topic
you want to monitor, logging in to Telegram, and starting the watcher. About
10–15 minutes. No prior Python or Telegram-API experience needed.

Prefer to do it manually? Skip to [`INSTALL.md`](INSTALL.md), or see the
**Manual quick start** section below.

> ⚠️ **You need an active Claude Pro subscription** — the watcher classifies
> messages through the `claude` CLI, not an Anthropic API key. Install the
> CLI from <https://claude.ai/code> and run `claude /login` once before
> starting.

---

## What you get

- **Realtime listener.** Every message in a watched group is captured into
  a local SQLite database.
- **AI relevance filter.** Each message is judged by Claude against the
  group's `topic_hint` (e.g. `gamedev`, `ai-startups`, `3d`). Only relevant
  messages get a `topic` and `summary`.
- **Local dashboard** at `http://127.0.0.1:8000` with three views:
  - **Feed** — recent relevant messages across all groups, filterable by time
    window.
  - **Daily digest** — relevant items grouped per day, per group.
  - **Digest window** — multi-day digest for retrospective scanning.
- **Daily cron digest.** At a configurable hour every day, the watcher
  re-scans the previous 24 hours of each group, in case the realtime listener
  missed anything or was offline.
- **Docker-ready.** One `docker compose up -d` runs the whole thing 24/7.

What it does **not** do (intentionally): no private DM classification, no
lead scoring, no Google Sheets export, no Telegram bot, no voice
transcription. If you need those, fork it and add them.

---

## Architecture (WAT)

Three layers, each with a single responsibility:

```
┌──────────────────────────────────────────────────────────┐
│  workflows/   markdown SOPs — what should happen          │
│                  (scan_group_daily.md, build_digest.md)   │
├──────────────────────────────────────────────────────────┤
│  agent        Claude — makes decisions, calls tools       │
│                  (run-time via tools/classifier.py)       │
├──────────────────────────────────────────────────────────┤
│  tools/       Python — does the work deterministically    │
│                  (telegram_client.py, message_store.py,   │
│                   classifier.py, group_scanner.py)        │
└──────────────────────────────────────────────────────────┘
```

The single entrypoint `app/supervisor.py` wires Telethon (group listener),
APScheduler (daily digest cron) and Uvicorn (dashboard) into one async loop.

```
TelegramWatcher/
├── app/
│   ├── supervisor.py        ← run this
│   ├── setup_session.py     ← one-shot Telegram login
│   ├── run_listener.py      ← realtime group handler
│   ├── run_daily_digest.py  ← cron job for daily digest
│   ├── build_digest_from_db.py
│   ├── scheduler.py
│   ├── dashboard.py
│   ├── config.py
│   ├── templates/           ← Jinja2 templates
│   └── static/              ← CSS / JS
├── tools/
│   ├── telegram_client.py   ← Telethon wrapper + flood retry
│   ├── claude_chat.py       ← shells out to `claude` CLI
│   ├── classifier.py        ← judge_group() — relevance LLM call
│   ├── message_store.py     ← SQLite repo (3 tables)
│   ├── group_scanner.py     ← daily/window scan
│   └── resolve_groups.py    ← convert @links → chat_ids
├── system_prompts/
│   └── group_relevance_filter.md  ← edit this to match your niche
├── workflows/
│   ├── scan_group_daily.md
│   └── build_daily_digest.md
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── INSTALL.md
```

---

## Manual quick start

For users who'd rather not use Claude Code as a wizard. See
[`INSTALL.md`](INSTALL.md) for the full step-by-step.

In short:

```bash
# 1. Clone and set up Python
git clone https://github.com/belilung/telegram-group-channel-AI-analyst.git TelegramWatcher
cd TelegramWatcher
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Get Telegram API credentials at https://my.telegram.org → API development tools
cp .env.example .env
# fill in TG_API_ID, TG_API_HASH, TG_PHONE, WATCHED_GROUPS_INIT

# 3. Install Claude CLI from https://claude.ai/code and log in (Claude Pro)
claude --version

# 4. One-shot Telegram login (enter the code Telegram sends you)
python -m app.setup_session

# 5. Run the watcher
python -m app.supervisor
```

Open `http://127.0.0.1:8000`.

### Docker

```bash
# log in once on the host so Claude CLI auth survives
claude --version

# one-shot Telegram code prompt
docker compose run --rm watcher python -m app.setup_session

# run 24/7
docker compose up -d
docker compose logs -f watcher
```

---

## Configuration

All config lives in `.env`. See `.env.example` for the full list.

Most-used knobs:

| Variable | Effect |
|----------|--------|
| `WATCHED_GROUPS_INIT` | Seed list of `<link>|<topic_hint>;...` on first run |
| `CLAUDE_MODEL` | Which Claude model to use (default `claude-haiku-4-5`) |
| `REALTIME_AI_FILTER` | `true` = classify on arrival; `false` = only daily cron |
| `DIGEST_CRON_HOUR` | Hour-of-day for the daily digest run (in `LOCAL_TZ`) |
| `MAX_MSGS_PER_GROUP` | Per-group cap for the daily scan |
| `CLASSIFY_CONCURRENCY` | How many parallel Claude calls (default 4) |

To change the relevance rules for your niche, edit
`system_prompts/group_relevance_filter.md`. That's the only AI prompt in the
project.

---

## Adding / removing watched groups

Three ways:

1. **`.env` on first run.** Set `WATCHED_GROUPS_INIT` and start the watcher.
   It calls `tools.resolve_groups.resolve_and_persist` exactly once if the
   `groups_watched` table is empty.
2. **Ad-hoc CLI.** Run `python -m app.setup_session` again — it re-resolves
   the env list.
3. **Direct DB.** Edit `data/telegram_watcher.db` → `groups_watched`. Flip
   `enabled` to 0 to pause a group, 1 to resume.

Group references can be:
- `@username` for public channels/groups
- `https://t.me/<username>` (same)
- `https://t.me/c/<internal_id>/<msg_id>` for private supergroups you're
  already a member of

---

## Tests

```bash
pytest -q
```

---

## License

MIT. Use it, fork it, sell it, hand it to your students — your call.
