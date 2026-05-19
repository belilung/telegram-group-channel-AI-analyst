# Installation

Two ways to run the watcher: directly with Python, or with Docker.
Either way you need three things:

1. **Telegram API credentials** (free, from `my.telegram.org`)
2. **Claude Pro subscription** + `claude` CLI installed
3. **Python 3.11+** (only for the non-Docker path)

---

## 1. Get Telegram API credentials

1. Open <https://my.telegram.org> in a browser. Log in with your phone.
2. Click **API development tools**.
3. Create an application (any name, any short name, platform = "Desktop").
4. Copy the **api_id** (number) and **api_hash** (long string).

Important: treat `api_hash` like a password. Never paste it into chats or
commit it.

---

## 2. Install the Claude CLI

The watcher uses your Claude Pro subscription via the `claude` CLI — no
Anthropic API key is needed.

```bash
# macOS / Linux
curl -fsSL https://claude.ai/install.sh | bash

# Log in (opens a browser)
claude /login
```

Verify:

```bash
claude --version
```

Make sure your Claude Pro subscription is active in <https://claude.ai>.

---

## 3a. Install — direct Python (recommended for development)

Requires Python 3.11 or newer.

```bash
git clone https://github.com/belilung/telegram-group-channel-AI-analyst.git TelegramWatcher
cd TelegramWatcher

python -m venv .venv
source .venv/bin/activate         # macOS / Linux
# .venv\Scripts\activate          # Windows

pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Open `.env` and fill in:

```dotenv
TG_API_ID=123456
TG_API_HASH=abcdef0123456789abcdef0123456789
TG_PHONE=+380XXXXXXXXX
TG_SESSION_NAME=telegram_watcher
CLAUDE_MODEL=claude-haiku-4-5

# Your initial list of groups/channels to monitor.
# Each entry:  <link or @username>|<topic_hint>
# Topic hint is a short tag (gamedev, ai-startups, 3d, frontend-jobs, ...).
WATCHED_GROUPS_INIT=@my_gamedev_channel|gamedev;https://t.me/c/1234567890/4350|3d
```

### One-shot Telegram login

```bash
python -m app.setup_session
```

Telegram will send you a code in the Telegram app itself. Paste it. If your
account has 2FA, you'll be asked for the password.

This creates a session file at `data/sessions/telegram_watcher.session` —
keep it safe (it's the equivalent of being logged in on a new device). It's
already in `.gitignore`.

### Run

```bash
python -m app.supervisor
```

You should see:

```
Supervisor: logged in id=12345 username=@you realtime_ai=True
Realtime group handler armed
Scheduler armed: daily_digest at 08:00 Europe/Kyiv
Dashboard at http://127.0.0.1:8000
```

Open <http://127.0.0.1:8000> in your browser.

To stop: `Ctrl-C`.

To run 24/7 on Linux, use a systemd unit, `pm2`, or simply `nohup`:

```bash
nohup .venv/bin/python -m app.supervisor > watcher.log 2>&1 &
```

---

## 3b. Install — Docker (recommended for a VPS or always-on box)

```bash
git clone https://github.com/belilung/telegram-group-channel-AI-analyst.git TelegramWatcher
cd TelegramWatcher
cp .env.example .env
# fill in TG_API_ID / TG_API_HASH / TG_PHONE / WATCHED_GROUPS_INIT
```

### Claude CLI inside Docker

The CLI uses your host's `~/.claude/` directory for auth. Make sure you've
run `claude /login` on the host first; the compose file mounts `~/.claude`
read-write into the container.

```bash
claude /login          # on the host
claude --version       # verify
```

### One-shot Telegram code prompt

```bash
docker compose run --rm watcher python -m app.setup_session
```

Paste the code Telegram sends you. Same for the 2FA password if you have one.

### Run 24/7

```bash
docker compose up -d
docker compose logs -f watcher
```

To stop:

```bash
docker compose down
```

The session file and SQLite database live in `./data/` on the host — they
survive container restarts. Back them up if you care about history.

---

## Troubleshooting

**`Code expired`** — start `setup_session` again, paste the code faster (or
delete an old code Telegram sent earlier).

**`claude CLI not found`** — install from <https://claude.ai/code>, then
re-source your shell. Inside Docker, make sure `~/.claude` is mounted and
contains the auth state.

**`FloodWaitError`** — Telegram is rate-limiting your account. The watcher
backs off automatically; just wait. If it persists, lower
`MAX_MSGS_PER_GROUP` and `CLASSIFY_CONCURRENCY` in `.env`.

**Dashboard shows no items** — make sure groups are actually in the
`groups_watched` table:

```bash
sqlite3 data/telegram_watcher.db 'SELECT chat_id, title, enabled, topic_hint FROM groups_watched;'
```

If empty, re-run `python -m app.setup_session` with a non-empty
`WATCHED_GROUPS_INIT`.

**Want the bot to classify only at digest time, not realtime?** Set
`REALTIME_AI_FILTER=false` in `.env`. Messages still get logged immediately;
classification waits for the daily cron.

---

## What to keep private

These never leave your machine; keep them out of git, chats, screenshots:

- `.env`
- `data/sessions/*.session`
- `data/telegram_watcher.db`
- Your Claude CLI auth at `~/.claude/`

All four are gitignored by default.
