"""QR-based Telegram login — bypasses SendCodeRequest rate-limit.

When Telegram silently rate-limits app-code delivery for a phone (codes never
arrive in Service Notifications despite Telegram returning SentCodeTypeApp),
the standard `app.setup_session` flow is unusable. This script uses Telegram's
`auth.exportLoginToken` API instead (Telethon's `client.qr_login()`), which
uses a different rate-limit pool and works as long as the user has any
already-logged-in Telegram client to scan the QR from.

Usage:
    python -m app.setup_session_qr

The script prints:
  - a Base64 `tg://login?token=...` URL,
  - an ASCII QR in the terminal,
  - a PNG file at data/sessions/qr.png.

The QR is auto-regenerated every ~25 seconds because Telegram's QR tokens
expire quickly. User scans QR from Telegram (mobile) via Settings → Devices →
Link Desktop Device. After confirmation, the session is saved and
WATCHED_GROUPS_INIT is resolved exactly the same way `setup_session.py` does it.

2FA password is requested via the same file-driven callback as in
`app/setup_session.py` so this script works both interactively and in
background.
"""

from __future__ import annotations

import asyncio
import logging
import sys

import qrcode
from telethon.errors import SessionPasswordNeededError

from app.config import get_settings
from app.setup_session import _build_password_callback
from tools.fs_security import secure_dir
from tools.message_store import MessageStore
from tools.resolve_groups import resolve_and_persist
from tools.telegram_client import build_client, secure_session_files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("setup_session_qr")

QR_TOTAL_TIMEOUT_SEC = 300
QR_REFRESH_INTERVAL_SEC = 25


def _print_qr(url, png_path) -> None:
    """Print ASCII QR to stdout and save a PNG copy."""
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)
    print("", flush=True)
    qr.print_ascii(invert=True)
    print("", flush=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(str(png_path))


async def _wait_for_scan(client, qr_login, png_path):
    """Loop: re-render QR every QR_REFRESH_INTERVAL_SEC until logged in or timeout.

    Returns the User on success.
    Raises SessionPasswordNeededError if 2FA is required (caller handles).
    Raises asyncio.TimeoutError if QR_TOTAL_TIMEOUT_SEC elapses.
    """
    loop = asyncio.get_event_loop()
    deadline = loop.time() + QR_TOTAL_TIMEOUT_SEC
    cycle = 0
    while True:
        cycle += 1
        print(
            f"--- QR refresh #{cycle} (valid ~{QR_REFRESH_INTERVAL_SEC}s) ---",
            flush=True,
        )
        print(f"QR_URL: {qr_login.url}", flush=True)
        _print_qr(qr_login.url, png_path)
        print(f"QR_PNG: {png_path}", flush=True)

        remaining = deadline - loop.time()
        if remaining <= 0:
            raise asyncio.TimeoutError("QR scan deadline reached")
        wait_for = min(QR_REFRESH_INTERVAL_SEC, remaining)
        try:
            return await qr_login.wait(timeout=wait_for)
        except asyncio.TimeoutError:
            await qr_login.recreate()
            continue


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

    pw_file = settings.sessions_dir / ".login_password"
    if pw_file.exists():
        pw_file.unlink()

    png_path = settings.sessions_dir / "qr.png"
    if png_path.exists():
        png_path.unlink()

    client = build_client(settings)
    print("Connecting to Telegram (QR login mode) ...", flush=True)
    await client.connect()

    try:
        qr_login = await client.qr_login()
        print(
            "Open Telegram on your phone → Settings → Devices → "
            "Link Desktop Device, then scan the QR below.",
            flush=True,
        )

        user = None
        try:
            user = await _wait_for_scan(client, qr_login, png_path)
        except SessionPasswordNeededError:
            print("2FA required.", flush=True)
            pw_callback = _build_password_callback(pw_file)
            password = pw_callback()
            if not password:
                print(
                    "ERROR: 2FA enabled but empty password provided.",
                    file=sys.stderr,
                )
                return 3
            user = await client.sign_in(password=password)
        except asyncio.TimeoutError:
            print(
                "ERROR: QR scan timed out — restart the script.",
                file=sys.stderr,
            )
            return 5

        if user is None:
            print("ERROR: QR login did not complete.", file=sys.stderr)
            return 4

        secure_session_files(settings)
        me = await client.get_me()
        print(
            f"Logged in as: id={me.id} username=@{getattr(me, 'username', None)}",
            flush=True,
        )

        init = settings.watched_groups_init.strip()
        if not init:
            print(
                "WATCHED_GROUPS_INIT is empty — skipping group resolution.",
                flush=True,
            )
        else:
            print("Resolving WATCHED_GROUPS_INIT ...", flush=True)
            resolved = await resolve_and_persist(client, store, init)
            print(f"Resolved {len(resolved)} groups:", flush=True)
            for r in resolved:
                topic = r.topic_hint or "-"
                print(
                    f"  - chat_id={r.chat_id}  topic={topic:<20}  title={r.title}",
                    flush=True,
                )
    finally:
        await client.disconnect()

    print(f"Done. Session saved to: {settings.session_file}", flush=True)
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
