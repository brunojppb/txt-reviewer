"""The MCP tools and prompts, called as plain functions."""

from __future__ import annotations

import json
import sqlite3

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from app import mcp_server, repo

LIGHTHOUSE = {
    "type": "doc",
    "content": [
        {"type": "heading", "content": [{"type": "text", "text": "The Lighthouse"}]},
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "The keeper had not spoken for days."}],
        },
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "He counted the very slow waves."}],
        },
    ],
}


@pytest.fixture()
def doc_id(conn: sqlite3.Connection) -> str:
    """Return the id of a document with three numbered paragraphs."""
    doc = repo.create_document(conn, "The Lighthouse")
    repo.update_content(conn, doc["id"], LIGHTHOUSE)
    return doc["id"]


@pytest.fixture()
def run(conn: sqlite3.Connection, doc_id: str, fake_passes) -> dict:
    """Start a run of the first pass over the document."""
    return mcp_server.start_run(doc_id, "cut-filler", "pytest")


def finding(quote: str, paragraph: int, note: str = "This word says nothing.") -> dict:
    """Return one finding for submit_findings."""
    return {"quote": quote, "paragraph": paragraph, "note": note}


# Reading


def test_list_documents(doc_id: str) -> None:
    documents = mcp_server.list_documents()
    assert [d["id"] for d in documents] == [doc_id]
    assert documents[0]["word_count"] == 15


def test_get_document_by_id_and_by_title(doc_id: str) -> None:
    by_id = mcp_server.get_document(doc_id)
    by_title = mcp_server.get_document("The Lighthouse")
    assert by_id == by_title
    assert by_id["paragraphs"][1] == {
        "n": 2,
        "text": "The keeper had not spoken for days.",
    }
    assert by_id["text"].startswith("[1] The Lighthouse\n\n[2] The keeper")


def test_get_document_unknown(db_file) -> None:
    with pytest.raises(ToolError):
        mcp_server.get_document("nope")


def test_list_and_get_pass(fake_passes) -> None:
    passes = mcp_server.list_passes()
    assert [p["slug"] for p in passes] == ["cut-filler", "long-sentences"]
    assert passes[0]["number"] == 0

    by_slug = mcp_server.get_pass("cut-filler")
    assert by_slug["prompt"] == "Find words that carry no meaning."
    assert mcp_server.get_pass("0")["id"] == by_slug["id"]
    assert mcp_server.get_pass(by_slug["id"])["slug"] == "cut-filler"


def test_get_pass_unknown(fake_passes) -> None:
    with pytest.raises(ToolError):
        mcp_server.get_pass("no-such-pass")


# Runs


def test_start_run(conn: sqlite3.Connection, doc_id: str, fake_passes) -> None:
    started = mcp_server.start_run(doc_id, "cut-filler", "pytest")
    assert started["document_id"] == doc_id
    assert started["pass_id"] == fake_passes[0]["id"]
    assert repo.get_run(conn, started["run_id"])["status"] == "running"
    assert repo.change_seq(conn, doc_id) == 1


def test_start_run_unknown_pass(doc_id: str, fake_passes) -> None:
    with pytest.raises(ToolError):
        mcp_server.start_run(doc_id, "no-such-pass")


def test_submit_findings_stores_open_findings(
    conn: sqlite3.Connection, doc_id: str, run: dict
) -> None:
    before = repo.change_seq(conn, doc_id)
    result = mcp_server.submit_findings(
        run["run_id"], [finding("very slow", 3), finding("for days", 2)]
    )
    assert result == {"accepted": 2, "rejected": []}
    assert repo.change_seq(conn, doc_id) > before

    findings = repo.list_findings(conn, doc_id)
    assert [f["quote"] for f in findings] == ["very slow", "for days"]
    assert {f["status"] for f in findings} == {"open"}
    assert [f["pass_slug"] for f in findings] == ["cut-filler", "cut-filler"]

    stored = repo.list_annotations(conn, doc_id)
    assert stored[0]["kind"] == "finding"
    assert stored[0]["source"] == "pass"
    assert stored[0]["anchored"] == 0
    assert repo.get_run(conn, run["run_id"])["finding_count"] == 2


def test_submit_findings_moves_a_quote_to_its_own_paragraph(
    conn: sqlite3.Connection, doc_id: str, run: dict
) -> None:
    result = mcp_server.submit_findings(run["run_id"], [finding("very slow", 2)])
    assert result["accepted"] == 1
    assert repo.list_findings(conn, doc_id)[0]["paragraph"] == 3


def test_submit_findings_rejects_a_quote_that_is_nowhere(
    conn: sqlite3.Connection, doc_id: str, run: dict
) -> None:
    result = mcp_server.submit_findings(
        run["run_id"], [finding("the lamp guttered", 2)]
    )
    assert result["accepted"] == 0
    assert result["rejected"] == [{"index": 0, "reason": "quote not found"}]
    assert repo.list_findings(conn, doc_id) == []


def test_submit_findings_rejects_an_unknown_paragraph(doc_id: str, run: dict) -> None:
    result = mcp_server.submit_findings(run["run_id"], [finding("very slow", 9)])
    assert result["rejected"] == [{"index": 0, "reason": "paragraph not found"}]


def test_submit_findings_checks_the_lengths(doc_id: str, run: dict) -> None:
    result = mcp_server.submit_findings(
        run["run_id"],
        [
            finding("", 2),
            finding("very slow", 3, ""),
            finding("x" * 301, 2),
        ],
    )
    assert result["accepted"] == 0
    assert [r["index"] for r in result["rejected"]] == [0, 1, 2]
    assert "quote" in result["rejected"][0]["reason"]
    assert "note" in result["rejected"][1]["reason"]


def test_submit_findings_folds_quotes(conn, doc_id: str, run: dict) -> None:
    result = mcp_server.submit_findings(run["run_id"], [finding("VERY   slow", 3)])
    assert result["accepted"] == 1


def test_submit_findings_unknown_run(db_file) -> None:
    with pytest.raises(ToolError):
        mcp_server.submit_findings("nope", [finding("a", 1)])


def test_finish_run(conn: sqlite3.Connection, doc_id: str, run: dict) -> None:
    mcp_server.submit_findings(run["run_id"], [finding("very slow", 3)])
    done = mcp_server.finish_run(run["run_id"], "one pass over the text")
    assert done == {"run_id": run["run_id"], "status": "done", "finding_count": 1}
    assert repo.get_run(conn, run["run_id"])["finished_at"]


def test_list_findings_reads_the_decisions(
    conn: sqlite3.Connection, doc_id: str, run: dict
) -> None:
    mcp_server.submit_findings(
        run["run_id"], [finding("very slow", 3), finding("for days", 2)]
    )
    mcp_server.finish_run(run["run_id"])
    first = repo.list_findings(conn, doc_id)[0]
    repo.set_annotation_status(conn, first["id"], "accepted")

    every = mcp_server.list_findings(doc_id)
    assert len(every) == 2
    accepted = mcp_server.list_findings(doc_id, status="accepted")
    assert [f["id"] for f in accepted] == [first["id"]]
    assert accepted[0]["note"] == "This word says nothing."
    assert mcp_server.list_findings(doc_id, pass_ref="long-sentences") == []


def test_list_findings_bad_status(doc_id: str, run: dict) -> None:
    with pytest.raises(ToolError):
        mcp_server.list_findings(doc_id, status="maybe")


def test_snapshot_revision(conn: sqlite3.Connection, doc_id: str) -> None:
    result = mcp_server.snapshot_revision(doc_id, "before the rewrite", True)
    revision = repo.get_revision(conn, result["revision_id"])
    assert revision["label"] == "before the rewrite"
    assert revision["is_major"] == 1
    assert json.loads(revision["content"]) == LIGHTHOUSE


# Prompts


def test_run_pass_prompt(doc_id: str, fake_passes) -> None:
    messages = mcp_server.run_pass("cut-filler", doc_id)
    assert [m.role for m in messages] == ["user", "user", "user"]
    assert "stern writing coach" in messages[0].content.text
    assert "Find words that carry no meaning." in messages[1].content.text
    assert doc_id in messages[2].content.text
    assert "submit_findings" in messages[2].content.text


def test_review_prompt_lists_every_enabled_pass(
    conn: sqlite3.Connection, doc_id: str, fake_passes
) -> None:
    repo.update_pass(
        conn, fake_passes[1]["id"], "Long sentences", "Sentences", "x", False
    )
    messages = mcp_server.review(doc_id)
    body = messages[1].content.text
    assert "cut-filler" in body
    assert "long-sentences" not in body
