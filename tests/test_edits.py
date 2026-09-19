"""Edits on a finding: the repo layer and the applied route."""

from __future__ import annotations

import sqlite3

import pytest

from app import repo


@pytest.fixture()
def finding(conn: sqlite3.Connection, fake_passes) -> dict:
    """Return one finding of the first fake pass."""
    doc = repo.create_document(conn, "Draft")
    pass_id = fake_passes[0]["id"]
    run = repo.create_run(conn, doc["id"], pass_id, "pytest")
    return repo.create_finding(
        conn, doc["id"], pass_id, run["id"], "you really have to", 1, "A hedge."
    )


def test_create_and_list_edits(conn: sqlite3.Connection, finding: dict) -> None:
    repo.create_edit(conn, finding["id"], 0, "really", "")
    repo.create_edit(conn, finding["id"], 1, "have to", "must")

    edits = repo.list_edits(conn, finding["id"])
    assert [(e["target"], e["replacement"]) for e in edits] == [
        ("really", ""),
        ("have to", "must"),
    ]
    assert {e["status"] for e in edits} == {"open"}


def test_apply_edit_hides_it_and_drops_the_count(
    conn: sqlite3.Connection, finding: dict
) -> None:
    first = repo.create_edit(conn, finding["id"], 0, "really", "")
    repo.create_edit(conn, finding["id"], 1, "have to", "must")
    assert repo.count_open_edits(conn, finding["id"]) == 2

    applied = repo.apply_edit(conn, first["id"])

    assert applied["status"] == "applied"
    assert [e["target"] for e in repo.list_edits(conn, finding["id"])] == ["have to"]
    assert repo.count_open_edits(conn, finding["id"]) == 1
    assert len(repo.list_edits(conn, finding["id"], open_only=False)) == 2


def test_annotation_carries_its_open_edits(
    conn: sqlite3.Connection, finding: dict
) -> None:
    repo.create_edit(conn, finding["id"], 0, "really", "")

    one = repo.get_annotation(conn, finding["id"])
    listed = repo.list_annotations(conn, one["document_id"])

    assert [e["target"] for e in one["edits"]] == ["really"]
    assert [e["target"] for e in listed[0]["edits"]] == ["really"]


def test_deleting_a_finding_deletes_its_edits(
    conn: sqlite3.Connection, finding: dict
) -> None:
    repo.create_edit(conn, finding["id"], 0, "really", "")

    repo.delete_annotation(conn, finding["id"])

    rows = conn.execute("SELECT COUNT(*) AS n FROM finding_edits").fetchone()
    assert rows["n"] == 0


def test_update_pass_stores_the_flag(
    conn: sqlite3.Connection, fake_passes: list[dict]
) -> None:
    target = fake_passes[1]
    assert target["suggests_edits"] == 0

    row = repo.update_pass(
        conn,
        target["id"],
        target["title"],
        target["group_name"],
        target["prompt"],
        True,
        True,
    )

    assert row["suggests_edits"] == 1
