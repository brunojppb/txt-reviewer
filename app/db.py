"""SQLite connection helper and schema setup."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DB_PATH = "data/app.db"


def db_path() -> Path:
    """Return the database path from the WORKSHOP_DB environment variable."""
    return Path(os.environ.get("WORKSHOP_DB", DEFAULT_DB_PATH))


def get_conn(path: str | Path) -> sqlite3.Connection:
    """Open a connection to the database at path with row access by name."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # One connection serves one request, but sync and async routes touch it
    # from different threads, so the same-thread check must be off.
    conn = sqlite3.connect(target, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: str | Path) -> None:
    """Create the tables at path if they do not exist yet."""
    script = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = get_conn(path)
    try:
        with conn:
            conn.executescript(script)
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """Yield a connection for one request. FastAPI overrides this in tests."""
    conn = get_conn(db_path())
    try:
        yield conn
    finally:
        conn.close()
