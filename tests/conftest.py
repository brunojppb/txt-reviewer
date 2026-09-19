"""Fixtures. Every test runs against a database in tmp_path."""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import repo
from app.db import get_conn, get_db, init_db
from app.main import app

# The seed file belongs to another agent, so the tests bring their own passes.
FAKE_PASSES = [
    {
        "slug": "cut-filler",
        "title": "Cut filler",
        "group": "Writing cleanup",
        "prompt": "Find words that carry no meaning.",
    },
    {
        "slug": "long-sentences",
        "title": "Long sentences",
        "group": "Sentences",
        "prompt": "Find sentences that run past what a reader holds.",
    },
]


@pytest.fixture()
def db_file(tmp_path, monkeypatch) -> Path:
    """Return the path of a migrated database and point the app at it."""
    path = tmp_path / "test.db"
    monkeypatch.setenv("WORKSHOP_DB", str(path))
    init_db(path)
    return path


@pytest.fixture()
def conn(db_file: Path) -> Iterator[sqlite3.Connection]:
    """Open one connection to the test database."""
    connection = get_conn(db_file)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture()
def fake_passes(conn: sqlite3.Connection) -> list[dict]:
    """Put two known passes in the database in place of the seeded ones."""
    with conn:
        conn.execute("DELETE FROM passes")
    repo.insert_passes(conn, FAKE_PASSES)
    return repo.list_passes(conn)


@pytest.fixture()
def client(db_file: Path) -> Iterator[TestClient]:
    """Serve the app against the test database.

    The host is 127.0.0.1 because the MCP endpoint turns away other hosts.
    """

    def override() -> Iterator[sqlite3.Connection]:
        connection = get_conn(db_file)
        try:
            yield connection
        finally:
            connection.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app, base_url="http://127.0.0.1:8000") as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_doc(client: TestClient) -> str:
    """Create a document and return its id."""
    response = client.post("/documents")
    assert response.status_code == 200
    assert response.content == b""
    return response.headers["HX-Redirect"].removeprefix("/documents/")


def make_annotation(client: TestClient, doc_id: str, kind: str = "comment") -> str:
    """Create an annotation and return its id."""
    aid = str(uuid.uuid4())
    response = client.post(
        f"/documents/{doc_id}/annotations", data={"id": aid, "kind": kind}
    )
    assert response.status_code == 200
    return aid


def doc_with(text: str) -> dict:
    """Return a TipTap document holding one paragraph of text."""
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }
