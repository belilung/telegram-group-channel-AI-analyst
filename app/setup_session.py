"""One-shot bootstrap. Works in two modes:

1. Interactive (TTY):
       python -m app.setup_session
   Prompts for the Telegram login code (and 2FA password if enabled).

2. File-driven (background-friendly):
       python -m app.setup_session
   When stdin is not a TTY, the script prints `NEED_CODE: <path>` and
   blocks until the caller writes the digits into that path. Same for
   `NEED_PASSWORD: <path>` on 2FA-enabled accounts. 5-minute timeout each.

Both modes then resolve WATCHED_GROUPS_INIT and save the session.
"""

from __future__ import annotations

import asyncio
import getpass
import logging
import sys
import time
from pathlib import Path

from app.config import get_settings
from tools.fs_security import secure_dir, secure_file
from tools.message_store import MessageStore
from tools.resolve_groups import resolve_and_persist
from tools.telegram_client import build_client, secure_session_files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("setup_session")

WAIT_TIMEOUT_SEC = 300


def _is_tty() -> bool:
    return sys.stdin.isatty()


def _build_code_callback(code_file: Path):
    """Return an async callback that resolves to the Telegram login code."""
    async def _cb() -> str:
        if _is_tty():
            return input("Enter Telegram login code: ").strip()
        print(f"NEED_CODE: {code_file}", flush=True)
        deadline = time.monotonic() + WAIT_TIMEOUT_SEC
        while not code_file.exists():
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Login code not delivered to {code_file} within "
                    f"{WAIT_TIMEOUT_SEC}s"
                )
            await asyncio.sleep(0.5)
        secure_file(code_file)
        try:
            return code_file.read_text().strip()
        finally:
            if code_file.exists():
                code_file.unlink()

    return _cb


def _build_password_callback(pw_file: Path):
    """Return a SYNC callback that resolves to the 2FA password.

    Telethon calls password callable without awaiting, so it has to be sync.
    """
    def _cb() -> str:
        if _is_tty():
            return getpass.getpass("Telegram 2FA password (Enter to skip): ")
        print(f"NEED_PASSWORD: {pw_file}", flush=True)
        deadline = time.monotonic() + WAIT_TIMEOUT_SEC
        while not pw_file.exists():
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"2FA password not delivered to {pw_file} within "
                    f"{WAIT_TIMEOUT_SEC}s"
                )
            time.sleep(0.5)
        secure_file(pw_file)
        try:
            return pw_file.read_text().strip()
        finally:
            if pw_file.exists():
                pw_file.unlink()

    return _cb


async def _run() -> int:
    settings = get_settings()
    try:
        settings.validate_runtime()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    secure_dir(settings.db_absolute_path.parent)
    secure_dir(settings.sessions_dir)
    store = MessageStore(str(settings.db_absolute_path))
    await store.init_schema()

    code_file = settings.sessions_dir / ".login_code"
    pw_file = settings.sessions_dir / ".login_password"
    # Clean any stale signal files from a previous attempt
    for f in (code_file, pw_file):
        if f.exists():
            f.unlink()

    client = build_client(settings)
    print(f"Connecting to Telegram as {settings.tg_phone} ...", flush=True)
    await client.start(
        phone=settings.tg_phone,
        code_callback=_build_code_callback(code_file),
        password=_build_password_callback(pw_file),
    )
    # Telethon has just written the .session file — lock it down to 0600.
    secure_session_files(settings)
    me = await client.get_me()
    print(
        f"Logged in as: id={me.id} username=@{getattr(me, 'username', None)}",
        flush=True,
    )

    if not settings.watched_groups_init.strip():
        print("WATCHED_GROUPS_INIT is empty — skipping group resolution.", flush=True)
    else:
        print("Resolving WATCHED_GROUPS_INIT ...", flush=True)
        resolved = await resolve_and_persist(
            client, store, settings.watched_groups_init
        )
        print(f"Resolved {len(resolved)} groups:", flush=True)
        for r in resolved:
            print(f"  - chat_id={r.chat_id}  topic={r.topic_hint or '-':<10}  title={r.title}", flush=True)

    await client.disconnect()
    print(f"Done. Session saved to: {settings.session_file}", flush=True)
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
