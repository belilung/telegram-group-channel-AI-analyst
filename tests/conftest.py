"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure project root is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> str:
    return str(tmp_path / "watcher_test.db")
