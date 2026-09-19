"""All SQL for documents, annotations, and revisions. Every function returns dicts."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

EMPTY_DOC = '{"type":"doc","content":[{"type":"paragraph"}]}'
KINDS = ("comment", "suggestion", "question")
STATUSES = ("open", "resolved")


def now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    """Return a fresh uuid4 string."""
    return str(uuid.uuid4())


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _rows(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


# Documents


def create_document(conn: sqlite3.Connection, title: str = "Untitled") -> dict[str, Any]:
    """Insert an empty document and return it."""
    doc_id = new_id()
    ts = now_iso()
    with conn:
        conn.execute(
            "INSERT INTO documents (id, title, content, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (doc_id, title or "Untitled", EMPTY_DOC, ts, ts),
        )
    doc = get_document(conn, doc_id)
    assert doc is not None
    return doc


def list_documents(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return every document, most recently updated first."""
    rows = conn.execute(
        "SELECT * FROM documents ORDER BY updated_at DESC, created_at DESC"
    ).fetchall()
    return _rows(rows)


def get_document(conn: sqlite3.Connection, doc_id: str) -> dict[str, Any] | None:
    """Return one document, or None when the id is unknown."""
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    return _row(row)


def update_title(conn: sqlite3.Connection, doc_id: str, title: str) -> dict[str, Any] | None:
    """Set the document title and return the document."""
    with conn:
        cur = conn.execute(
            "UPDATE documents SET title = ?, updated_at = ? WHERE id = ?",
            (title or "Untitled", now_iso(), doc_id),
        )
    if cur.rowcount == 0:
        return None
    return get_document(conn, doc_id)


def update_content(conn: sqlite3.Connection, doc_id: str, content: Any) -> str | None:
    """Store the document content and return the new updated_at."""
    ts = now_iso()
    with conn:
        cur = conn.execute(
            "UPDATE documents SET content = ?, updated_at = ? WHERE id = ?",
            (json.dumps(content), ts, doc_id),
        )
    return ts if cur.rowcount else None


def delete_document(conn: sqlite3.Connection, doc_id: str) -> bool:
    """Delete a document with its annotations and revisions."""
    with conn:
        cur = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    return cur.rowcount > 0


# Annotations


def list_annotations(conn: sqlite3.Connection, doc_id: str) -> list[dict[str, Any]]:
    """Return the annotations of a document, oldest first."""
    rows = conn.execute(
        "SELECT * FROM annotations WHERE document_id = ? ORDER BY created_at, id",
        (doc_id,),
    ).fetchall()
    return _rows(rows)


def get_annotation(conn: sqlite3.Connection, aid: str) -> dict[str, Any] | None:
    """Return one annotation, or None when the id is unknown."""
    row = conn.execute("SELECT * FROM annotations WHERE id = ?", (aid,)).fetchone()
    return _row(row)


def create_annotation(
    conn: sqlite3.Connection, doc_id: str, aid: str, kind: str
) -> dict[str, Any] | None:
    """Insert an annotation with an empty body. Return None when the id is taken."""
    ts = now_iso()
    try:
        with conn:
            conn.execute(
                "INSERT INTO annotations (id, document_id, kind, body, status,"
                " created_at, updated_at) VALUES (?, ?, ?, '', 'open', ?, ?)",
                (aid, doc_id, kind, ts, ts),
            )
    except sqlite3.IntegrityError:
        return None
    return get_annotation(conn, aid)


def update_annotation_body(
    conn: sqlite3.Connection, aid: str, body: str
) -> dict[str, Any] | None:
    """Set the annotation body and return the annotation."""
    with conn:
        cur = conn.execute(
            "UPDATE annotations SET body = ?, updated_at = ? WHERE id = ?",
            (body, now_iso(), aid),
        )
    if cur.rowcount == 0:
        return None
    return get_annotation(conn, aid)


def set_annotation_status(
    conn: sqlite3.Connection, aid: str, status: str
) -> dict[str, Any] | None:
    """Set the annotation status and return the annotation."""
    with conn:
        cur = conn.execute(
            "UPDATE annotations SET status = ?, updated_at = ? WHERE id = ?",
            (status, now_iso(), aid),
        )
    if cur.rowcount == 0:
        return None
    return get_annotation(conn, aid)


def delete_annotation(conn: sqlite3.Connection, aid: str) -> bool:
    """Delete one annotation."""
    with conn:
        cur = conn.execute("DELETE FROM annotations WHERE id = ?", (aid,))
    return cur.rowcount > 0


# Revisions


def list_revisions(conn: sqlite3.Connection, doc_id: str) -> list[dict[str, Any]]:
    """Return the revisions of a document, newest first, without snapshot payloads."""
    rows = conn.execute(
        "SELECT id, document_id, label, is_major, created_at FROM revisions"
        " WHERE document_id = ? ORDER BY created_at DESC, rowid DESC",
        (doc_id,),
    ).fetchall()
    return _rows(rows)


def get_revision(conn: sqlite3.Connection, rid: str) -> dict[str, Any] | None:
    """Return one revision with its snapshot, or None when the id is unknown."""
    row = conn.execute("SELECT * FROM revisions WHERE id = ?", (rid,)).fetchone()
    return _row(row)


def create_revision(
    conn: sqlite3.Connection, doc_id: str, label: str = "", is_major: bool = False
) -> dict[str, Any] | None:
    """Snapshot the current content and annotations of a document."""
    doc = get_document(conn, doc_id)
    if doc is None:
        return None
    rid = new_id()
    snapshot = json.dumps(list_annotations(conn, doc_id))
    with conn:
        conn.execute(
            "INSERT INTO revisions (id, document_id, content, annotations, label,"
            " is_major, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (rid, doc_id, doc["content"], snapshot, label, 1 if is_major else 0, now_iso()),
        )
    return get_revision(conn, rid)


def flag_revision(
    conn: sqlite3.Connection, rid: str, is_major: bool, label: str
) -> dict[str, Any] | None:
    """Set the major flag and label of a revision."""
    with conn:
        cur = conn.execute(
            "UPDATE revisions SET is_major = ?, label = ? WHERE id = ?",
            (1 if is_major else 0, label, rid),
        )
    if cur.rowcount == 0:
        return None
    return get_revision(conn, rid)


def restore_revision(conn: sqlite3.Connection, rid: str) -> dict[str, Any] | None:
    """Snapshot the document as "Before restore", then copy the revision content back."""
    revision = get_revision(conn, rid)
    if revision is None:
        return None
    doc_id = revision["document_id"]
    if create_revision(conn, doc_id, label="Before restore") is None:
        return None
    with conn:
        conn.execute(
            "UPDATE documents SET content = ?, updated_at = ? WHERE id = ?",
            (revision["content"], now_iso(), doc_id),
        )
    return get_document(conn, doc_id)
