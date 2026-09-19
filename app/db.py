"""SQLite connection helper, migrations, and seeding."""

from __future__ import annotations

import logging
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DB_PATH = "data/app.db"
SCHEMA_VERSION = 3

logger = logging.getLogger(__name__)

# Version 2 adds the editing passes. The annotations table gains columns and
# wider CHECK constraints, so SQLite needs a new table and a copy.
MIGRATION_2 = """
BEGIN;

CREATE TABLE passes (
  id TEXT PRIMARY KEY,
  position INTEGER NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  group_name TEXT NOT NULL,
  prompt TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE runs (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  pass_id TEXT NOT NULL REFERENCES passes(id) ON DELETE CASCADE,
  agent TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL CHECK (status IN ('running','done','failed')),
  note TEXT NOT NULL DEFAULT '',
  finding_count INTEGER NOT NULL DEFAULT 0,
  started_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE TABLE annotations_v2 (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('comment','suggestion','question','finding')),
  source TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual','pass')),
  pass_id TEXT REFERENCES passes(id) ON DELETE SET NULL,
  run_id TEXT REFERENCES runs(id) ON DELETE SET NULL,
  quote TEXT NOT NULL DEFAULT '',
  paragraph INTEGER,
  anchored INTEGER NOT NULL DEFAULT 1,
  body TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','accepted','rejected')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

INSERT INTO annotations_v2
  (id, document_id, kind, source, quote, anchored, body, status, created_at, updated_at)
SELECT id, document_id, kind, 'manual', '', 1, body,
       CASE status WHEN 'resolved' THEN 'accepted' ELSE 'open' END,
       created_at, updated_at
FROM annotations;

DROP TABLE annotations;
ALTER TABLE annotations_v2 RENAME TO annotations;

CREATE INDEX idx_annotations_document ON annotations(document_id, created_at);
CREATE INDEX idx_annotations_pass ON annotations(document_id, pass_id);
CREATE INDEX idx_runs_document ON runs(document_id, pass_id, started_at);

ALTER TABLE documents ADD COLUMN change_seq INTEGER NOT NULL DEFAULT 0;

COMMIT;
"""

# The passes whose findings may carry wording. Each one maps a span of text to
# a cut or to one plain equivalent.
SUGGESTING_SLUGS = (
    "sand-off-filler-words",
    "cut-hedges-and-intensifiers",
    "cut-redundant-pairs",
    "cut-redundant-modifiers",
    "cut-redundant-categories",
    "replace-phrases-with-words",
    "turn-negatives-into-affirmatives",
    "trim-metadiscourse",
    "delete-empty-verbs",
)


def _sql_slug_list(slugs: tuple[str, ...]) -> str:
    """Return the slugs as a quoted, comma-joined SQL literal list."""
    return ",\n  ".join("'" + slug.replace("'", "''") + "'" for slug in slugs)


# Version 3 lets a finding carry wording. No CHECK constraint on an existing
# table changes, so SQLite needs no copy of a table here. The slug list comes
# from SUGGESTING_SLUGS so the two cannot drift apart.
MIGRATION_3 = f"""
BEGIN;

ALTER TABLE passes ADD COLUMN suggests_edits INTEGER NOT NULL DEFAULT 0;

CREATE TABLE finding_edits (
  id TEXT PRIMARY KEY,
  annotation_id TEXT NOT NULL REFERENCES annotations(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  target TEXT NOT NULL,
  replacement TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','applied')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX idx_finding_edits_annotation
  ON finding_edits(annotation_id, position);

UPDATE passes SET suggests_edits = 1 WHERE slug IN (
  {_sql_slug_list(SUGGESTING_SLUGS)}
);

COMMIT;
"""


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


def user_version(conn: sqlite3.Connection) -> int:
    """Return the schema version of the database."""
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def migrate(conn: sqlite3.Connection) -> None:
    """Bring the database up to the current schema version."""
    version = user_version(conn)
    if version >= SCHEMA_VERSION:
        return
    # Rebuilding the annotations table would trip the foreign keys of rows
    # that point at it, so the check stays off until the copy is done.
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        if version < 1:
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            conn.execute("PRAGMA user_version = 1")
        if version < 2:
            conn.executescript(MIGRATION_2)
            conn.execute("PRAGMA user_version = 2")
        if version < 3:
            conn.executescript(MIGRATION_3)
            conn.execute("PRAGMA user_version = 3")
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def seed_passes(conn: sqlite3.Connection) -> int:
    """Insert the seeded passes when the table is empty. Return how many landed."""
    if conn.execute("SELECT COUNT(*) FROM passes").fetchone()[0]:
        return 0
    try:
        from app.seed_passes import PASSES
    except ImportError:
        logger.warning("app.seed_passes is missing, so no editing pass was seeded")
        return 0
    from app import repo

    return repo.insert_passes(conn, PASSES)


def init_db(path: str | Path) -> None:
    """Migrate the database at path and seed the editing passes."""
    conn = get_conn(path)
    try:
        migrate(conn)
        seed_passes(conn)
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """Yield a connection for one request. FastAPI overrides this in tests."""
    conn = get_conn(db_path())
    try:
        yield conn
    finally:
        conn.close()
