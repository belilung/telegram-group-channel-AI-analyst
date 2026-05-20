"""Filesystem-permission helpers for sensitive secrets and state.

POSIX-only effect. On Windows (`os.name == "nt"`) chmod is a silent no-op,
because NTFS ACLs need a different API and breaking install on Windows for
a non-applicable security control is worse than silently skipping it.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_IS_WINDOWS = os.name == "nt"


def secure_file(path: str | Path) -> None:
    """chmod 0600 on `path`. Logs a warning on failure, never raises."""
    if _IS_WINDOWS:
        return
    p = Path(path)
    if not p.exists():
        return
    try:
        p.chmod(0o600)
    except OSError as e:
        logger.warning("secure_file(%s) failed: %s", p, e)


def secure_dir(path: str | Path) -> None:
    """chmod 0700 on `path` (creates it if missing). Logs and continues on failure."""
    if _IS_WINDOWS:
        Path(path).mkdir(parents=True, exist_ok=True)
        return
    p = Path(path)
    try:
        p.mkdir(parents=True, exist_ok=True)
        p.chmod(0o700)
    except OSError as e:
        logger.warning("secure_dir(%s) failed: %s", p, e)
