"""The MCP server. An agent runs editing passes over a document through it.

Every tool is a plain function that opens its own connection, so tests call
them directly.
"""

from __future__ import annotations

import sqlite3
from typing import Any, NotRequired, TypedDict

from mcp.server.mcpserver import MCPServer, Message, UserMessage
from mcp.server.mcpserver.exceptions import ToolError

from app import repo, text
from app.coach import COACH, STEPS
from app.db import db_path, get_conn

QUOTE_MAX = 300
NOTE_MAX = 600
REPLACEMENT_MAX = 120

server = MCPServer("workshop", instructions=COACH)


class Edit(TypedDict):
    """One change a finding offers. An empty replacement means cut."""

    target: str
    replacement: str


class Finding(TypedDict):
    """One problem in the text: the quote, its paragraph, the note, the edits."""

    quote: str
    paragraph: int
    note: str
    edits: NotRequired[list[Edit]]


def connect() -> sqlite3.Connection:
    """Open a connection to the workshop database."""
    return get_conn(db_path())


def _normalize(value: str) -> str:
    """Fold a quote so small differences of shape stop mattering."""
    folded = (
        value.replace("‘", "'")
        .replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
    )
    return " ".join(folded.split()).casefold()


def _holds(haystack: str, needle: str) -> bool:
    """Say whether a paragraph holds a quote, exactly or in folded form."""
    return needle in haystack or _normalize(needle) in _normalize(haystack)


def find_paragraph(
    paras: list[dict[str, Any]], quote: str, preferred: int
) -> int | None:
    """Return the number of the paragraph that holds the quote, or None."""
    for para in paras:
        if para["n"] == preferred and _holds(para["text"], quote):
            return preferred
    for para in paras:
        if _holds(para["text"], quote):
            return int(para["n"])
    return None


def _need_document(conn: sqlite3.Connection, ref: str) -> dict[str, Any]:
    doc = repo.find_document(conn, ref)
    if doc is None:
        raise ToolError(f"no document with the id or title {ref!r}")
    return doc


def _need_pass(conn: sqlite3.Connection, ref: str) -> dict[str, Any]:
    found = repo.find_pass(conn, ref)
    if found is None:
        raise ToolError(f"no pass with the id, slug, or number {ref!r}")
    return found


def _need_run(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    run = repo.get_run(conn, run_id)
    if run is None:
        raise ToolError(f"no run with the id {run_id!r}")
    return run


def _pass_view(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "number": row["position"],
        "slug": row["slug"],
        "title": row["title"],
        "group": row["group_name"],
        "enabled": bool(row["enabled"]),
        "suggests_edits": bool(row["suggests_edits"]),
    }


# Tools


@server.tool()
def list_documents() -> list[dict[str, Any]]:
    """List the documents in the workshop, most recently changed first."""
    conn = connect()
    try:
        return [
            {
                "id": doc["id"],
                "title": doc["title"],
                "updated_at": doc["updated_at"],
                "word_count": text.document_word_count(doc["content"]),
            }
            for doc in repo.list_documents(conn)
        ]
    finally:
        conn.close()


@server.tool()
def get_document(document: str) -> dict[str, Any]:
    """Read one document as numbered paragraphs. Give an id or an exact title."""
    conn = connect()
    try:
        doc = _need_document(conn, document)
        paras = text.paragraphs(doc["content"])
        return {
            "id": doc["id"],
            "title": doc["title"],
            "word_count": text.word_count(paras),
            "paragraphs": paras,
            "text": text.render(paras),
        }
    finally:
        conn.close()


@server.tool()
def list_passes() -> list[dict[str, Any]]:
    """List the editing passes in order."""
    conn = connect()
    try:
        return [_pass_view(row) for row in repo.list_passes(conn)]
    finally:
        conn.close()


@server.tool()
def get_pass(pass_ref: str) -> dict[str, Any]:
    """Read one pass with its prompt. Give an id, a slug, or a number."""
    conn = connect()
    try:
        found = _need_pass(conn, pass_ref)
        view = _pass_view(found)
        view["prompt"] = found["prompt"]
        return view
    finally:
        conn.close()


@server.tool()
def start_run(document: str, pass_ref: str, agent: str = "") -> dict[str, Any]:
    """Start a run of one pass over one document."""
    conn = connect()
    try:
        doc = _need_document(conn, document)
        found = _need_pass(conn, pass_ref)
        run = repo.create_run(conn, doc["id"], found["id"], agent)
        repo.bump_change_seq(conn, doc["id"])
        return {
            "run_id": run["id"],
            "document_id": doc["id"],
            "pass_id": found["id"],
        }
    finally:
        conn.close()


def _edit_reason(edit: Any, quote: str, suggests: bool) -> str | None:
    """Return why this edit cannot stand, or None when it can."""
    if not suggests:
        return "pass does not suggest wording"
    target = str(edit.get("target", "")).strip()
    if not 1 <= len(target) <= QUOTE_MAX:
        return "target too long"
    if len(str(edit.get("replacement", "")).strip()) > REPLACEMENT_MAX:
        return "replacement too long"
    if not _holds(quote, target):
        return "target not in quote"
    return None


@server.tool()
def submit_findings(run_id: str, findings: list[Finding]) -> dict[str, Any]:
    """Submit every finding of a run in one call. A finding may carry edits."""
    conn = connect()
    try:
        run = _need_run(conn, run_id)
        doc = _need_document(conn, run["document_id"])
        paras = text.paragraphs(doc["content"])
        found_pass = repo.get_pass(conn, run["pass_id"])
        suggests = bool(found_pass and found_pass["suggests_edits"])

        accepted = 0
        rejected: list[dict[str, Any]] = []
        edits_dropped: list[dict[str, Any]] = []
        for index, finding in enumerate(findings):
            quote = str(finding.get("quote", "")).strip()
            note = str(finding.get("note", "")).strip()
            try:
                paragraph = int(finding.get("paragraph", 0))
            except (TypeError, ValueError):
                paragraph = 0

            if not 1 <= len(quote) <= QUOTE_MAX:
                rejected.append(
                    {
                        "index": index,
                        "reason": f"quote must be 1 to {QUOTE_MAX} characters",
                    }
                )
                continue
            if not 1 <= len(note) <= NOTE_MAX:
                rejected.append(
                    {"index": index, "reason": f"note must be 1 to {NOTE_MAX} characters"}
                )
                continue
            if not any(p["n"] == paragraph for p in paras):
                rejected.append({"index": index, "reason": "paragraph not found"})
                continue
            number = find_paragraph(paras, quote, paragraph)
            if number is None:
                rejected.append({"index": index, "reason": "quote not found"})
                continue

            created = repo.create_finding(
                conn, doc["id"], run["pass_id"], run["id"], quote, number, note
            )
            accepted += 1

            position = 0
            for edit in finding.get("edits") or []:
                reason = _edit_reason(edit, quote, suggests)
                if reason is not None:
                    edits_dropped.append(
                        {
                            "index": index,
                            "target": str(edit.get("target", "")).strip(),
                            "reason": reason,
                        }
                    )
                    continue
                repo.create_edit(
                    conn,
                    created["id"],
                    position,
                    str(edit.get("target", "")).strip(),
                    str(edit.get("replacement", "")).strip(),
                )
                position += 1

        if accepted:
            repo.add_findings_to_run(conn, run["id"], accepted)
        repo.bump_change_seq(conn, doc["id"])
        return {
            "accepted": accepted,
            "rejected": rejected,
            "edits_dropped": edits_dropped,
        }
    finally:
        conn.close()


@server.tool()
def finish_run(run_id: str, note: str = "") -> dict[str, Any]:
    """Close a run. Call it once, after submit_findings."""
    conn = connect()
    try:
        run = _need_run(conn, run_id)
        done = repo.finish_run(conn, run["id"], "done", note)
        assert done is not None
        repo.bump_change_seq(conn, run["document_id"])
        return {
            "run_id": done["id"],
            "status": done["status"],
            "finding_count": done["finding_count"],
        }
    finally:
        conn.close()


@server.tool()
def list_findings(
    document: str, pass_ref: str | None = None, status: str | None = None
) -> list[dict[str, Any]]:
    """Read the findings of a document and what the writer did with each one."""
    conn = connect()
    try:
        doc = _need_document(conn, document)
        pass_id = _need_pass(conn, pass_ref)["id"] if pass_ref else None
        if status is not None and status not in repo.STATUSES:
            raise ToolError(f"status must be one of {', '.join(repo.STATUSES)}")
        return repo.list_findings(conn, doc["id"], pass_id, status)
    finally:
        conn.close()


@server.tool()
def snapshot_revision(
    document: str, label: str = "", is_major: bool = False
) -> dict[str, Any]:
    """Store a revision of a document before the writer rewrites it."""
    conn = connect()
    try:
        doc = _need_document(conn, document)
        revision = repo.create_revision(conn, doc["id"], label, is_major)
        if revision is None:
            raise ToolError("the snapshot failed")
        return {"revision_id": revision["id"]}
    finally:
        conn.close()


# Prompts


@server.prompt()
def run_pass(pass_ref: str, document: str) -> list[Message]:
    """Run one editing pass over one document."""
    conn = connect()
    try:
        found = _need_pass(conn, pass_ref)
        doc = _need_document(conn, document)
    finally:
        conn.close()
    return [
        UserMessage(COACH),
        UserMessage(f"The pass is {found['title']} ({found['slug']}).\n\n{found['prompt']}"),
        UserMessage(
            f"The document is {doc['title']} (id {doc['id']}).\n\n{STEPS}"
        ),
    ]


@server.prompt()
def review(document: str) -> list[Message]:
    """Run every enabled pass over one document, one run for each."""
    conn = connect()
    try:
        doc = _need_document(conn, document)
        passes = repo.list_passes(conn, enabled_only=True)
    finally:
        conn.close()
    listing = "\n".join(
        f"{p['position']}. {p['title']} ({p['slug']})" for p in passes
    )
    return [
        UserMessage(COACH),
        UserMessage(
            f"Review {doc['title']} (id {doc['id']}). Run these passes in order,"
            f" one run each. Read the prompt of a pass with get_pass before you"
            f" run it.\n\n{listing}"
        ),
        UserMessage(STEPS),
    ]
