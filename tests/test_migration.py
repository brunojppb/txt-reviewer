"""The step from the bones schema to the editing passes."""

from __future__ import annotations

import sys
import types

from app import db, repo
from tests.conftest import FAKE_PASSES

BONES_SCHEMA = db.SCHEMA_PATH.read_text(encoding="utf-8")
CONTENT = '{"type":"doc","content":[{"type":"paragraph"}]}'


def make_version_1(path) -> None:
    """Write a database that holds the bones schema and one of each row."""
    conn = db.get_conn(path)
    with conn:
        conn.executescript(BONES_SCHEMA)
        conn.execute(
            "INSERT INTO documents (id, title, content, created_at, updated_at)"
            " VALUES ('d1', 'Old draft', ?, '2026-01-01T00:00:00+00:00',"
            " '2026-01-02T00:00:00+00:00')",
            (CONTENT,),
        )
        conn.execute(
            "INSERT INTO annotations (id, document_id, kind, body, status,"
            " created_at, updated_at) VALUES ('a1', 'd1', 'comment', 'Cut this',"
            " 'resolved', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
        )
        conn.execute(
            "INSERT INTO annotations (id, document_id, kind, body, status,"
            " created_at, updated_at) VALUES ('a2', 'd1', 'question', 'Why?',"
            " 'open', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
        )
        conn.execute(
            "INSERT INTO revisions (id, document_id, content, annotations, label,"
            " is_major, created_at) VALUES ('r1', 'd1', ?, '[]', 'v1', 1,"
            " '2026-01-01T00:00:00+00:00')",
            (CONTENT,),
        )
    conn.close()


def test_migration_keeps_the_rows_and_maps_resolved(tmp_path, monkeypatch) -> None:
    path = tmp_path / "old.db"
    monkeypatch.setenv("WORKSHOP_DB", str(path))
    make_version_1(path)

    db.init_db(path)

    conn = db.get_conn(path)
    assert db.user_version(conn) == db.SCHEMA_VERSION
    doc = repo.get_document(conn, "d1")
    assert doc["title"] == "Old draft"
    assert doc["change_seq"] == 0
    assert len(repo.list_revisions(conn, "d1")) == 1

    annotations = {a["id"]: a for a in repo.list_annotations(conn, "d1")}
    assert annotations["a1"]["status"] == "accepted"
    assert annotations["a2"]["status"] == "open"
    assert annotations["a1"]["source"] == "manual"
    assert annotations["a1"]["anchored"] == 1
    conn.close()


def test_migration_runs_once(tmp_path, monkeypatch) -> None:
    path = tmp_path / "twice.db"
    monkeypatch.setenv("WORKSHOP_DB", str(path))
    db.init_db(path)
    db.init_db(path)

    conn = db.get_conn(path)
    assert db.user_version(conn) == db.SCHEMA_VERSION
    conn.close()


def fake_seed_module() -> types.ModuleType:
    """Return a stand-in for app.seed_passes holding two passes."""
    module = types.ModuleType("app.seed_passes")
    module.PASSES = FAKE_PASSES
    return module


def test_seed_runs_once(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "app.seed_passes", fake_seed_module())
    path = tmp_path / "seeded.db"
    db.init_db(path)
    db.init_db(path)

    conn = db.get_conn(path)
    passes = repo.list_passes(conn)
    conn.close()
    assert [p["slug"] for p in passes] == ["cut-filler", "long-sentences"]
    assert [p["position"] for p in passes] == [0, 1]


def test_missing_seed_file_seeds_nothing(tmp_path, monkeypatch) -> None:
    # None in sys.modules makes the import fail, as it does before the file lands.
    monkeypatch.setitem(sys.modules, "app.seed_passes", None)
    path = tmp_path / "bare.db"
    db.init_db(path)

    conn = db.get_conn(path)
    assert repo.list_passes(conn) == []
    conn.close()


def test_migration_adds_edits_and_the_pass_flag(tmp_path, monkeypatch) -> None:
    path = tmp_path / "v3.db"
    monkeypatch.setenv("WORKSHOP_DB", str(path))
    make_version_1(path)

    db.init_db(path)

    conn = db.get_conn(path)
    assert db.user_version(conn) == 3
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(passes)")}
    assert "suggests_edits" in columns
    tables = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert "finding_edits" in tables
    # The rows of version 1 survive the step.
    assert repo.get_document(conn, "d1")["title"] == "Old draft"
    conn.close()


def test_the_migration_flags_a_pass_that_is_already_there(tmp_path) -> None:
    """A database that already holds the seeded passes gains the flag."""
    path = tmp_path / "flags.db"
    conn = db.get_conn(path)
    with conn:
        conn.executescript(BONES_SCHEMA)
        conn.executescript(db.MIGRATION_2)
        conn.execute(
            "INSERT INTO passes (id, position, slug, title, group_name, prompt,"
            " enabled, created_at, updated_at) VALUES ('p1', 0,"
            " 'sand-off-filler-words', 'Sand off filler words', 'Writing cleanup',"
            " 'x', 1, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
        )
        conn.execute("PRAGMA user_version = 2")

    db.migrate(conn)

    assert repo.get_pass(conn, "p1")["suggests_edits"] == 1
    assert len(db.SUGGESTING_SLUGS) == 9
    conn.close()


def test_seeding_flags_the_suggesting_passes(tmp_path, monkeypatch) -> None:
    path = tmp_path / "seed-flags.db"
    monkeypatch.setenv("WORKSHOP_DB", str(path))

    db.init_db(path)

    conn = db.get_conn(path)
    flagged = {p["slug"] for p in repo.list_passes(conn) if p["suggests_edits"]}
    conn.close()
    assert flagged == set(db.SUGGESTING_SLUGS)
