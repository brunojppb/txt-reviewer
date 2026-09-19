"""All SQL for the workshop tool. Every function returns dicts."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

EMPTY_DOC = '{"type":"doc","content":[{"type":"paragraph"}]}'
KINDS = ("comment", "suggestion", "question")
STATUSES = ("open", "accepted", "rejected")
CLOSED_STATUSES = ("accepted", "rejected")


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


def find_document(conn: sqlite3.Connection, ref: str) -> dict[str, Any] | None:
    """Return one document by id or by exact title."""
    doc = get_document(conn, ref)
    if doc is not None:
        return doc
    row = conn.execute(
        "SELECT * FROM documents WHERE title = ? ORDER BY updated_at DESC LIMIT 1",
        (ref,),
    ).fetchone()
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


def closed_annotation_ids(conn: sqlite3.Connection, doc_id: str) -> list[str]:
    """Return ids of a document's annotations that are accepted or rejected."""
    rows = conn.execute(
        "SELECT id FROM annotations WHERE document_id = ? AND status != 'open'",
        (doc_id,),
    ).fetchall()
    return [row["id"] for row in rows]


def list_annotations(
    conn: sqlite3.Connection, doc_id: str, open_only: bool = False
) -> list[dict[str, Any]]:
    """Return the annotations of a document, oldest first, with the pass slug."""
    where = "a.document_id = ?"
    if open_only:
        where += " AND a.status = 'open'"
    rows = conn.execute(
        "SELECT a.*, p.slug AS pass_slug, p.title AS pass_title FROM annotations a"
        f" LEFT JOIN passes p ON p.id = a.pass_id WHERE {where}"
        " ORDER BY a.created_at, a.id",
        (doc_id,),
    ).fetchall()
    return _attach_edits(conn, _rows(rows))


def get_annotation(conn: sqlite3.Connection, aid: str) -> dict[str, Any] | None:
    """Return one annotation, or None when the id is unknown."""
    row = conn.execute(
        "SELECT a.*, p.slug AS pass_slug, p.title AS pass_title FROM annotations a"
        " LEFT JOIN passes p ON p.id = a.pass_id WHERE a.id = ?",
        (aid,),
    ).fetchone()
    annotation = _row(row)
    if annotation is None:
        return None
    return _attach_edits(conn, [annotation])[0]


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


# Change counter


def bump_change_seq(conn: sqlite3.Connection, doc_id: str) -> int:
    """Raise the change counter of a document and return the new value."""
    with conn:
        conn.execute(
            "UPDATE documents SET change_seq = change_seq + 1 WHERE id = ?", (doc_id,)
        )
    return change_seq(conn, doc_id)


def change_seq(conn: sqlite3.Connection, doc_id: str) -> int:
    """Return the change counter of a document."""
    row = conn.execute(
        "SELECT change_seq FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    return int(row["change_seq"]) if row is not None else 0


# Findings


def create_finding(
    conn: sqlite3.Connection,
    doc_id: str,
    pass_id: str,
    run_id: str,
    quote: str,
    paragraph: int,
    note: str,
) -> dict[str, Any] | None:
    """Insert one finding of a run. The browser anchors it later."""
    aid = new_id()
    ts = now_iso()
    with conn:
        conn.execute(
            "INSERT INTO annotations (id, document_id, kind, source, pass_id, run_id,"
            " quote, paragraph, anchored, body, status, created_at, updated_at)"
            " VALUES (?, ?, 'finding', 'pass', ?, ?, ?, ?, 0, ?, 'open', ?, ?)",
            (aid, doc_id, pass_id, run_id, quote, paragraph, note, ts, ts),
        )
    return get_annotation(conn, aid)


def set_anchored(
    conn: sqlite3.Connection, aid: str, anchored: bool
) -> dict[str, Any] | None:
    """Record whether the browser found the quote of a finding."""
    with conn:
        cur = conn.execute(
            "UPDATE annotations SET anchored = ? WHERE id = ?",
            (1 if anchored else 0, aid),
        )
    if cur.rowcount == 0:
        return None
    return get_annotation(conn, aid)


def list_unanchored_findings(
    conn: sqlite3.Connection, doc_id: str
) -> list[dict[str, Any]]:
    """Return the open findings of a document that carry no highlight yet."""
    rows = conn.execute(
        "SELECT a.id, a.pass_id, p.slug AS pass_slug, a.quote, a.paragraph"
        " FROM annotations a LEFT JOIN passes p ON p.id = a.pass_id"
        " WHERE a.document_id = ? AND a.source = 'pass' AND a.anchored = 0"
        " AND a.status = 'open' ORDER BY a.created_at, a.id",
        (doc_id,),
    ).fetchall()
    return _rows(rows)


def list_findings(
    conn: sqlite3.Connection,
    doc_id: str,
    pass_id: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return the findings of a document, oldest first."""
    where = "a.document_id = ? AND a.source = 'pass'"
    args: list[Any] = [doc_id]
    if pass_id:
        where += " AND a.pass_id = ?"
        args.append(pass_id)
    if status:
        where += " AND a.status = ?"
        args.append(status)
    rows = conn.execute(
        "SELECT a.id, p.slug AS pass_slug, a.quote, a.paragraph, a.body AS note,"
        f" a.status, a.created_at FROM annotations a"
        f" LEFT JOIN passes p ON p.id = a.pass_id WHERE {where}"
        " ORDER BY a.created_at, a.id",
        args,
    ).fetchall()
    return _rows(rows)


# Edits


def _attach_edits(
    conn: sqlite3.Connection, annotations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Put each annotation's open edits on it, in position order."""
    for annotation in annotations:
        annotation["edits"] = []
    ids = [a["id"] for a in annotations]
    if not ids:
        return annotations
    marks = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT * FROM finding_edits WHERE annotation_id IN ({marks})"
        " AND status = 'open' ORDER BY position, created_at",
        ids,
    ).fetchall()
    by_id = {a["id"]: a for a in annotations}
    for row in rows:
        by_id[row["annotation_id"]]["edits"].append(dict(row))
    return annotations


def create_edit(
    conn: sqlite3.Connection,
    annotation_id: str,
    position: int,
    target: str,
    replacement: str,
) -> dict[str, Any] | None:
    """Insert one edit of a finding and return it."""
    eid = new_id()
    ts = now_iso()
    with conn:
        conn.execute(
            "INSERT INTO finding_edits (id, annotation_id, position, target,"
            " replacement, status, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, 'open', ?, ?)",
            (eid, annotation_id, position, target, replacement, ts, ts),
        )
    return get_edit(conn, eid)


def get_edit(conn: sqlite3.Connection, eid: str) -> dict[str, Any] | None:
    """Return one edit, or None when the id is unknown."""
    row = conn.execute("SELECT * FROM finding_edits WHERE id = ?", (eid,)).fetchone()
    return _row(row)


def list_edits(
    conn: sqlite3.Connection, annotation_id: str, open_only: bool = True
) -> list[dict[str, Any]]:
    """Return the edits of a finding in position order."""
    where = "annotation_id = ?"
    if open_only:
        where += " AND status = 'open'"
    rows = conn.execute(
        f"SELECT * FROM finding_edits WHERE {where} ORDER BY position, created_at",
        (annotation_id,),
    ).fetchall()
    return _rows(rows)


def apply_edit(conn: sqlite3.Connection, eid: str) -> dict[str, Any] | None:
    """Mark one edit applied and return it."""
    with conn:
        cur = conn.execute(
            "UPDATE finding_edits SET status = 'applied', updated_at = ?"
            " WHERE id = ? AND status = 'open'",
            (now_iso(), eid),
        )
    if cur.rowcount == 0:
        return None
    return get_edit(conn, eid)


def count_open_edits(conn: sqlite3.Connection, annotation_id: str) -> int:
    """Return how many edits of a finding still wait for the writer."""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM finding_edits"
        " WHERE annotation_id = ? AND status = 'open'",
        (annotation_id,),
    ).fetchone()
    return int(row["n"])


# Passes


def slugify(text: str) -> str:
    """Return a kebab-case slug for a pass title."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "pass"


def _free_slug(conn: sqlite3.Connection, slug: str) -> str:
    """Return the slug, with a number added when it is taken."""
    taken = {
        row["slug"] for row in conn.execute("SELECT slug FROM passes").fetchall()
    }
    if slug not in taken:
        return slug
    n = 2
    while f"{slug}-{n}" in taken:
        n += 1
    return f"{slug}-{n}"


def list_passes(
    conn: sqlite3.Connection, enabled_only: bool = False
) -> list[dict[str, Any]]:
    """Return the passes in display order."""
    where = " WHERE enabled = 1" if enabled_only else ""
    rows = conn.execute(
        f"SELECT * FROM passes{where} ORDER BY position, created_at"
    ).fetchall()
    return _rows(rows)


def get_pass(conn: sqlite3.Connection, pid: str) -> dict[str, Any] | None:
    """Return one pass by id, or None when the id is unknown."""
    row = conn.execute("SELECT * FROM passes WHERE id = ?", (pid,)).fetchone()
    return _row(row)


def find_pass(conn: sqlite3.Connection, ref: str | int) -> dict[str, Any] | None:
    """Return one pass by id, slug, or number."""
    text = str(ref).strip()
    row = conn.execute(
        "SELECT * FROM passes WHERE id = ? OR slug = ?", (text, text)
    ).fetchone()
    if row is not None:
        return _row(row)
    if text.lstrip("-").isdigit():
        row = conn.execute(
            "SELECT * FROM passes WHERE position = ?", (int(text),)
        ).fetchone()
    return _row(row)


def insert_passes(conn: sqlite3.Connection, entries: list[dict[str, Any]]) -> int:
    """Insert seed passes in list order. Return how many landed."""
    ts = now_iso()
    count = 0
    with conn:
        for position, entry in enumerate(entries):
            slug = str(entry.get("slug") or slugify(str(entry.get("title", ""))))
            conn.execute(
                "INSERT OR IGNORE INTO passes (id, position, slug, title, group_name,"
                " prompt, enabled, suggests_edits, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
                (
                    new_id(),
                    position,
                    slug,
                    str(entry.get("title", slug)),
                    str(entry.get("group", "")),
                    str(entry.get("prompt", "")),
                    1 if entry.get("suggests_edits") else 0,
                    ts,
                    ts,
                ),
            )
            count += 1
    return count


def create_pass(
    conn: sqlite3.Connection, title: str, group_name: str, prompt: str
) -> dict[str, Any]:
    """Add a pass at the end of the list."""
    pid = new_id()
    ts = now_iso()
    row = conn.execute("SELECT MAX(position) AS last FROM passes").fetchone()
    position = 0 if row["last"] is None else int(row["last"]) + 1
    with conn:
        conn.execute(
            "INSERT INTO passes (id, position, slug, title, group_name, prompt,"
            " enabled, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (
                pid,
                position,
                _free_slug(conn, slugify(title)),
                title or "Untitled pass",
                group_name,
                prompt,
                ts,
                ts,
            ),
        )
    found = get_pass(conn, pid)
    assert found is not None
    return found


def update_pass(
    conn: sqlite3.Connection,
    pid: str,
    title: str,
    group_name: str,
    prompt: str,
    enabled: bool,
    suggests_edits: bool,
) -> dict[str, Any] | None:
    """Store the fields of a pass and return it."""
    with conn:
        cur = conn.execute(
            "UPDATE passes SET title = ?, group_name = ?, prompt = ?, enabled = ?,"
            " suggests_edits = ?, updated_at = ? WHERE id = ?",
            (
                title or "Untitled pass",
                group_name,
                prompt,
                1 if enabled else 0,
                1 if suggests_edits else 0,
                now_iso(),
                pid,
            ),
        )
    if cur.rowcount == 0:
        return None
    return get_pass(conn, pid)


def delete_pass(conn: sqlite3.Connection, pid: str) -> bool:
    """Delete one pass."""
    with conn:
        cur = conn.execute("DELETE FROM passes WHERE id = ?", (pid,))
    return cur.rowcount > 0


def move_pass(conn: sqlite3.Connection, pid: str, direction: str) -> bool:
    """Swap a pass with the one above or below it."""
    current = get_pass(conn, pid)
    if current is None:
        return False
    if direction == "up":
        order, compare = "DESC", "<"
    else:
        order, compare = "ASC", ">"
    neighbour = conn.execute(
        f"SELECT * FROM passes WHERE position {compare} ? ORDER BY position {order}"
        " LIMIT 1",
        (current["position"],),
    ).fetchone()
    if neighbour is None:
        return False
    ts = now_iso()
    with conn:
        conn.execute(
            "UPDATE passes SET position = ?, updated_at = ? WHERE id = ?",
            (neighbour["position"], ts, current["id"]),
        )
        conn.execute(
            "UPDATE passes SET position = ?, updated_at = ? WHERE id = ?",
            (current["position"], ts, neighbour["id"]),
        )
    return True


# Runs


def create_run(
    conn: sqlite3.Connection, doc_id: str, pass_id: str, agent: str = ""
) -> dict[str, Any]:
    """Start a run of one pass over one document."""
    rid = new_id()
    with conn:
        conn.execute(
            "INSERT INTO runs (id, document_id, pass_id, agent, status, note,"
            " finding_count, started_at) VALUES (?, ?, ?, ?, 'running', '', 0, ?)",
            (rid, doc_id, pass_id, agent, now_iso()),
        )
    found = get_run(conn, rid)
    assert found is not None
    return found


def get_run(conn: sqlite3.Connection, rid: str) -> dict[str, Any] | None:
    """Return one run, or None when the id is unknown."""
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (rid,)).fetchone()
    return _row(row)


def add_findings_to_run(conn: sqlite3.Connection, rid: str, count: int) -> None:
    """Raise the finding count of a run."""
    with conn:
        conn.execute(
            "UPDATE runs SET finding_count = finding_count + ? WHERE id = ?",
            (count, rid),
        )


def finish_run(
    conn: sqlite3.Connection, rid: str, status: str = "done", note: str = ""
) -> dict[str, Any] | None:
    """Close a run and return it."""
    with conn:
        cur = conn.execute(
            "UPDATE runs SET status = ?, note = ?, finished_at = ? WHERE id = ?",
            (status, note, now_iso(), rid),
        )
    if cur.rowcount == 0:
        return None
    return get_run(conn, rid)


def pass_status(conn: sqlite3.Connection, doc_id: str) -> dict[str, dict[str, Any]]:
    """Return the run and finding counts of each pass for one document."""
    row = conn.execute(
        "SELECT MAX(created_at) AS at FROM revisions"
        " WHERE document_id = ? AND is_major = 1",
        (doc_id,),
    ).fetchone()
    since = row["at"] or ""

    status: dict[str, dict[str, Any]] = {}
    runs = conn.execute(
        "SELECT pass_id,"
        " SUM(CASE WHEN status = 'done'"
        "   AND COALESCE(finished_at, started_at) > ? THEN 1 ELSE 0 END) AS done,"
        " MAX(CASE WHEN status = 'done' THEN finished_at END) AS last_finished"
        " FROM runs WHERE document_id = ? GROUP BY pass_id",
        (since, doc_id),
    ).fetchall()
    for run in runs:
        status[run["pass_id"]] = {
            "done": int(run["done"] or 0),
            "last_finished": run["last_finished"],
            "open": 0,
            "accepted": 0,
        }

    counts = conn.execute(
        "SELECT pass_id,"
        " SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_count,"
        " SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) AS accepted_count"
        " FROM annotations WHERE document_id = ? AND source = 'pass'"
        " AND pass_id IS NOT NULL GROUP BY pass_id",
        (doc_id,),
    ).fetchall()
    for count in counts:
        entry = status.setdefault(
            count["pass_id"],
            {"done": 0, "last_finished": None, "open": 0, "accepted": 0},
        )
        entry["open"] = int(count["open_count"] or 0)
        entry["accepted"] = int(count["accepted_count"] or 0)
    return status
