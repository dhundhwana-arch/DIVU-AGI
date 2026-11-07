"""Alembic migration round-trip on a clean database (acceptance test A11)."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str], database_url: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(
        {
            "PYTHONPATH": str(BACKEND_ROOT),
            "DIVU_APP_ENV": "test",
            "DIVU_SECRET_KEY": "migration-secret-key-with-sufficient-length-0",
            "DIVU_DATABASE_URL": database_url,
            "DIVU_LOG_LEVEL": "ERROR",
        }
    )
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_alembic_upgrade_and_downgrade(tmp_path: Path) -> None:
    database = tmp_path / f"{uuid.uuid4().hex}.db"
    url = f"sqlite+aiosqlite:///{database}"

    upgraded = _run(["upgrade", "head"], url)
    assert upgraded.returncode == 0, upgraded.stderr
    assert database.exists()

    import sqlite3

    connection = sqlite3.connect(database)
    tables = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    connection.close()
    assert {
        "users",
        "roles",
        "user_roles",
        "refresh_tokens",
        "api_keys",
        "provider_credentials",
        "audit_logs",
        "usage_events",
    } <= tables

    downgraded = _run(["downgrade", "base"], url)
    assert downgraded.returncode == 0, downgraded.stderr

    connection = sqlite3.connect(database)
    remaining = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    connection.close()
    assert remaining == {"alembic_version"}
