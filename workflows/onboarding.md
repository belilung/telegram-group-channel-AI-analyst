# First-run onboarding workflow

> Language: **English**. If the user writes to you in Russian, switch to
> [`onboarding.ru.md`](onboarding.ru.md) instead.

You are guiding a first-time user who just cloned this repo and ran `claude`
in the project root. They probably have **never used Claude Code, Telegram
MTProto, or a Python virtualenv before**. Your job is to walk them from
zero to a running `app.supervisor` with a populated dashboard.

## How to run this workflow

- Go through steps **in order**. Do not skip ahead.
- At each step: explain what we're about to do in 1–2 sentences, then
  execute it (run a command, ask a question, write a file).
- After each step that wrote anything to disk or asked the user something,
  print a single line: `✓ Step N complete` and what was done. If something
  failed, print `✗ Step N failed: <one-line reason>` and run the diagnostic
  block for that step.
- Be patient. The user can pause at any step — wait for them.
- **Secrets discipline:** once you have a value like `api_hash`, `phone`,
  or 2FA password, write it where it belongs (the `.env` file or the
  temp-file the setup script asked for) and **never** repeat the value in
  your replies. To confirm, quote only the first 4 chars + length:
  `"api_hash 'cd06…' (32 chars) ✓"`.

## Greeting

Start with something like:

> Hi! I'll help you set up Telegram Watcher. It's about 10–15 minutes of
> work; I'll guide you through each step. You'll need:
>
> 1. Your Telegram account (the phone number it's registered to).
> 2. About 5 minutes to grab API credentials at https://my.telegram.org.
> 3. An active **Claude Pro** subscription (we use the `claude` CLI, no
>    Anthropic API key needed).
>
> Ready? I'll start with checking your machine.

Wait for any acknowledgment before continuing.

---

## Step 1 — Preflight checks

Run these and report which (if any) are missing:

```bash
python3 --version
claude --version
git --version
```

Required: Python **3.11+**, Claude CLI any recent version, git any version.

**If `python3 --version` is < 3.11 or missing:**
- macOS: `brew install python@3.11`
- Ubuntu/Debian: `sudo apt update && sudo apt install -y python3.11 python3.11-venv`
- Windows: download from <https://www.python.org/downloads/> and re-run.

**If `claude --version` errors with "command not found":**
- macOS / Linux: `curl -fsSL https://claude.ai/install.sh | bash`, then
  re-source the shell (`exec $SHELL`).
- Windows: see <https://claude.ai/code>.

**If `git --version` is missing:** unlikely (the user cloned the repo), but
tell them to install Git from <https://git-scm.com>.

Pause until everything reports a version. **✓ Step 1 complete** when all
three succeed.

---

## Step 2 — Claude Pro authentication

The watcher uses the user's Claude subscription to classify messages.

Ask the user to run **on their host machine** (not via you):

```bash
claude /login
```

This opens a browser for OAuth. After they confirm they've logged in, verify
with:

```bash
claude --version
```

Also remind them that their Claude Pro plan must be active at
<https://claude.ai>. **✓ Step 2 complete** when they confirm login finished.

---

## Step 3 — Get Telegram API credentials

Ask the user to do this in a browser (you cannot do it for them):

1. Open <https://my.telegram.org>.
2. Log in with their Telegram phone number — Telegram sends a code in the
   Telegram app itself.
3. Click **API development tools**.
4. Create an application: any title, any short name, **platform = Desktop**.
5. Copy the two values: **`api_id`** (a number, ~7 digits) and **`api_hash`**
   (a 32-character hex string).

Tell them: `api_hash` is a password. Don't paste it in chats or commit it.

Then ask them to send you both values **here**. Example phrasing:

> Please send me your `api_id` and `api_hash`. I'll put them in `.env` and
> won't echo them back.

Validate after receiving:
- `api_id` parses as a positive integer.
- `api_hash` is exactly 32 hex characters (`^[0-9a-fA-F]{32}$`).

If validation fails, ask them to re-copy the value carefully.
**✓ Step 3 complete** when both validate.

---

## Step 4 — Phone number

Ask:

> What's the phone number of the Telegram account you want the watcher to
> use? Use international format with a leading `+`, e.g. `+380501234567`.
>
> ⚠️  Telegram's ToS sit in a grey area for user-account automation.
> **Use a dedicated, secondary phone number** for the watcher rather than
> your main personal account. If you don't have one, get a cheap eSIM or
> a second-line virtual number first.

Validate: must start with `+` and contain 10–15 digits after it.
**✓ Step 4 complete** on a valid phone.

---

## Step 5 — Write `.env`

Copy `.env.example` to `.env` and fill in the values you collected.

```bash
cp .env.example .env
```

Then use `Edit` to fill in:

```dotenv
TG_API_ID=<from step 3>
TG_API_HASH=<from step 3>
TG_PHONE=<from step 4>
```

Leave the other defaults as-is for now (model, db_path, dashboard host/port,
digest cron, behaviour knobs). We'll fill `WATCHED_GROUPS_INIT` in step 8.

Lock down the file (no-op on Windows; harmless):

```bash
chmod 600 .env
```

**✓ Step 5 complete:** confirm to the user that `.env` is written and
locked (`api_hash 'XXXX…' (32 chars), phone 'XXXX' (Y digits) → .env, mode
600`).

---

## Step 6 — Python virtual environment + dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate            # macOS / Linux
# .venv\Scripts\activate             # Windows PowerShell
pip install -r requirements.txt
```

This takes 1–2 minutes. Watch the output. If `pip install` fails with a
build error (common on Apple Silicon for some C extensions), the fix is
usually `pip install --upgrade pip setuptools wheel` first, then retry.

**✓ Step 6 complete** when `pip install` finishes without errors.

---

## Step 7 — Pick a topic hint

Explain to the user:

> The watcher runs each new Telegram message through Claude with a
> **relevance filter** — Claude judges whether the message matches the
> topic of the group. A **topic hint** is a short tag like `gamedev`,
> `ai-startups`, `3d`, `frontend-jobs`, `marketing-ua`. It guides what
> counts as "relevant".
>
> What topic would you like to monitor?

If they ask what the filter actually does, show them the first ~40 lines of
`system_prompts/group_relevance_filter.md`. The same prompt is the only AI
behaviour file in the project — they can edit it later to tune the filter
to their niche.

A topic hint can be reused across multiple groups, or each group can have
its own. We'll wire that in the next step.

**✓ Step 7 complete** once they give you one or more topic hints.

---

## Step 8 — Choose groups / channels to watch

Ask:

> Which Telegram groups or channels should I watch? Send me a list. Each
> entry can be:
>
> - `@public_handle` for public groups/channels (you can find this in the
>   group info screen in Telegram).
> - `https://t.me/<handle>` (same thing).
> - `https://t.me/c/<internal_id>/<msg_id>` for **private** supergroups you
>   are already a member of. To get this link: in Telegram desktop, right-
>   click any message in the group → "Copy Message Link". The
>   `c/<internal_id>` part is what we need.
>
> Pair each one with a topic hint from step 7. For example:
>
> ```
> @indiegamedevs gamedev
> https://t.me/c/1234567890/4350 3d
> @ai_news ai-startups
> ```

Once they give you the list, build the `WATCHED_GROUPS_INIT` string in the
exact format Telegram Watcher expects: `<link>|<topic_hint>;...`

So the example above becomes:

```
WATCHED_GROUPS_INIT=@indiegamedevs|gamedev;https://t.me/c/1234567890/4350|3d;@ai_news|ai-startups
```

Update `.env` to add that line.
**✓ Step 8 complete** when `.env` has a non-empty `WATCHED_GROUPS_INIT`.

---

## Step 9 — Telegram login (one-shot)

This authenticates the user account with Telegram and creates a session
file. Run:

```bash
python -m app.setup_session
```

Telegram will send a **login code** to the user's Telegram app. The
`setup_session` script will print one of two things:

- **TTY mode (typical):** it will prompt `Enter Telegram login code:`. Ask
  the user for the code in chat, then type it into the running process.
- **Non-TTY mode (sometimes inside containers / non-interactive shells):**
  it will print `NEED_CODE: /path/to/tmpfile` and wait. In that case ask
  the user for the code, then write it to that file:
  `echo "12345" > /path/to/tmpfile`.

**If the account has 2FA:** the same flow happens for the 2FA cloud
password. Use the temp-file callback (`NEED_PASSWORD: /path/...`) — **do
not** echo the password into a normal stdin pipe; it would end up in shell
history.

If you get `Code expired`, just re-run the command; Telegram sends a fresh
code.

On success, you'll see something like `Session written to
data/sessions/telegram_watcher.session` and `Resolved N groups`.

**✓ Step 9 complete** when the session is written and the seed groups
resolved.

---

## Step 10 — Smoke test

Run the test suite quickly to confirm the environment is healthy:

```bash
pytest -q
```

This takes <30 seconds. If anything fails, **stop here** and diagnose
before launching the supervisor. Read the failing test name and the actual
error (don't just retry).

**✓ Step 10 complete** when `pytest` exits 0.

---

## Step 11 — Launch the supervisor

This is the 24/7 process: realtime listener + scheduler + dashboard, all
in one event loop.

```bash
python -m app.supervisor
```

Wait for these log lines (they should appear within 5 seconds):

```
Supervisor: logged in id=<your_id> username=@<you> realtime_ai=True
Realtime group handler armed
Scheduler armed: daily_digest at 08:00 Europe/Kyiv
Dashboard at http://127.0.0.1:8000
```

Then open <http://127.0.0.1:8000> in the user's browser. The **Feed** view
should load. It might be empty initially — that's expected, messages only
appear as they're posted in the watched groups.

To stop the supervisor: `Ctrl-C`.

To run it permanently:

```bash
nohup .venv/bin/python -m app.supervisor > watcher.log 2>&1 &
```

(Linux/macOS; for Docker or systemd, see `INSTALL.md`.)

**✓ Step 11 complete** when the dashboard loads in the browser.

---

## Step 12 — What's next

Tell the user, in a short summary:

- **Logs:** `tail -f watcher.log` (if they used `nohup`), otherwise watch
  the terminal where the supervisor is running.
- **Add or remove groups later:** edit `WATCHED_GROUPS_INIT` in `.env` and
  re-run `python -m app.setup_session`. It re-resolves the env list and
  upserts groups in the DB.
- **Tune the relevance filter:** edit
  `system_prompts/group_relevance_filter.md`. That's the only AI prompt in
  the project. After editing, restart the supervisor for the change to take
  effect for realtime classification.
- **Daily digest:** runs automatically every day at the hour you set with
  `DIGEST_CRON_HOUR` in `.env` (default 08:00 in `LOCAL_TZ`). You can also
  trigger it manually: `python -m app.run_daily_digest`.
- **Production / VPS deployment:** see `INSTALL.md` § 3b (Docker) and the
  Security section for dashboard auth tokens and exposing it outside
  localhost.
- **Privacy reminder:** `.env`, `data/sessions/*.session`, and
  `data/telegram_watcher.db` are all in `.gitignore` already. Don't share
  them. If you suspect your account is compromised, see `INSTALL.md` §
  Security → "If you suspect your account is compromised".

End with a final self-check: ask them to confirm the dashboard is loading
and feed messages appear (the feed may take a few minutes if the groups
are quiet). 🎉

---

## Failure recovery cheatsheet

If any step fails and the user wants to start fresh:

```bash
rm -f .env
rm -rf data/
deactivate 2>/dev/null
rm -rf .venv
```

Then re-run this workflow from step 1.
