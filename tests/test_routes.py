"""Route tests against a temporary database."""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.db import get_conn, get_db, init_db
from app.main import app

DOC = {"type": "doc", "content": [{"type": "paragraph"}]}


def doc_with(text: str) -> dict:
    """Return a TipTap document holding one paragraph of text."""
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


@pytest.fixture()
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    """Serve the app against a database in tmp_path."""
    path = tmp_path / "test.db"
    monkeypatch.setenv("WORKSHOP_DB", str(path))
    init_db(path)

    def override() -> Iterator[sqlite3.Connection]:
        conn = get_conn(path)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_doc(client: TestClient) -> str:
    """Create a document and return its id."""
    response = client.post("/documents")
    assert response.status_code == 200
    assert response.content == b""
    location = response.headers["HX-Redirect"]
    return location.removeprefix("/documents/")


def make_annotation(client: TestClient, doc_id: str, kind: str = "comment") -> str:
    """Create an annotation and return its id."""
    aid = str(uuid.uuid4())
    response = client.post(
        f"/documents/{doc_id}/annotations", data={"id": aid, "kind": kind}
    )
    assert response.status_code == 200
    return aid


# Documents


def test_index_lists_documents(client: TestClient) -> None:
    doc_id = make_doc(client)
    response = client.get("/")
    assert response.status_code == 200
    assert f"/documents/{doc_id}" in response.text


def test_create_document_redirects(client: TestClient) -> None:
    response = client.post("/documents")
    assert response.status_code == 200
    assert response.headers["HX-Redirect"].startswith("/documents/")


def test_document_page_embeds_doc_data(client: TestClient) -> None:
    doc_id = make_doc(client)
    response = client.get(f"/documents/{doc_id}")
    assert response.status_code == 200
    assert 'id="doc-data"' in response.text
    assert 'id="sidebar"' in response.text
    assert 'id="save-status"' in response.text


def test_missing_document_is_404(client: TestClient) -> None:
    assert client.get("/documents/nope").status_code == 404


def test_update_title(client: TestClient) -> None:
    doc_id = make_doc(client)
    response = client.post(f"/documents/{doc_id}/title", data={"title": "Draft one"})
    assert response.status_code == 200
    assert "Draft one" in response.text
    assert "Draft one" in client.get("/").text


def test_update_title_missing_document(client: TestClient) -> None:
    response = client.post("/documents/nope/title", data={"title": "x"})
    assert response.status_code == 404


def test_delete_document(client: TestClient) -> None:
    doc_id = make_doc(client)
    response = client.request("DELETE", f"/documents/{doc_id}")
    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == "/"
    assert client.get(f"/documents/{doc_id}").status_code == 404


def test_autosave_content(client: TestClient) -> None:
    doc_id = make_doc(client)
    response = client.put(
        f"/documents/{doc_id}/content", json={"content": doc_with("Hello")}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["updated_at"]
    assert "Hello" in client.get(f"/documents/{doc_id}").text


def test_autosave_rejects_bad_content(client: TestClient) -> None:
    doc_id = make_doc(client)
    bad = client.put(
        f"/documents/{doc_id}/content", json={"content": {"type": "paragraph"}}
    )
    assert bad.status_code == 400
    missing = client.put(f"/documents/{doc_id}/content", json={})
    assert missing.status_code == 400
    broken = client.put(
        f"/documents/{doc_id}/content",
        content=b"not json",
        headers={"content-type": "application/json"},
    )
    assert broken.status_code == 400


def test_autosave_missing_document(client: TestClient) -> None:
    response = client.put("/documents/nope/content", json={"content": DOC})
    assert response.status_code == 404


# Annotations


def test_create_annotation(client: TestClient) -> None:
    doc_id = make_doc(client)
    aid = str(uuid.uuid4())
    response = client.post(
        f"/documents/{doc_id}/annotations", data={"id": aid, "kind": "suggestion"}
    )
    assert response.status_code == 200
    assert f'data-annotation-id="{aid}"' in response.text
    assert 'data-kind="suggestion"' in response.text


def test_create_annotation_duplicate_id_is_409(client: TestClient) -> None:
    doc_id = make_doc(client)
    aid = make_annotation(client, doc_id)
    again = client.post(
        f"/documents/{doc_id}/annotations", data={"id": aid, "kind": "comment"}
    )
    assert again.status_code == 409


def test_create_annotation_bad_kind_is_400(client: TestClient) -> None:
    doc_id = make_doc(client)
    response = client.post(
        f"/documents/{doc_id}/annotations",
        data={"id": str(uuid.uuid4()), "kind": "praise"},
    )
    assert response.status_code == 400


def test_annotation_list(client: TestClient) -> None:
    doc_id = make_doc(client)
    aid = make_annotation(client, doc_id)
    response = client.get(f"/documents/{doc_id}/annotations")
    assert response.status_code == 200
    assert aid in response.text


def test_update_annotation_body(client: TestClient) -> None:
    doc_id = make_doc(client)
    aid = make_annotation(client, doc_id)
    response = client.put(f"/annotations/{aid}", data={"body": "Cut this line"})
    assert response.status_code == 200
    assert "Cut this line" in response.text


def test_resolve_annotation(client: TestClient) -> None:
    doc_id = make_doc(client)
    aid = make_annotation(client, doc_id)
    response = client.post(f"/annotations/{aid}/status", data={"status": "resolved"})
    assert response.status_code == 200
    assert 'data-status="resolved"' in response.text
    reopened = client.post(f"/annotations/{aid}/status", data={"status": "open"})
    assert 'data-status="open"' in reopened.text


def test_bad_status_is_400(client: TestClient) -> None:
    doc_id = make_doc(client)
    aid = make_annotation(client, doc_id)
    response = client.post(f"/annotations/{aid}/status", data={"status": "maybe"})
    assert response.status_code == 400


def test_annotation_routes_404(client: TestClient) -> None:
    assert client.put("/annotations/nope", data={"body": "x"}).status_code == 404
    assert client.post("/annotations/nope/status", data={"status": "open"}).status_code == 404
    assert client.request("DELETE", "/annotations/nope").status_code == 404


def test_delete_annotation_sends_trigger(client: TestClient) -> None:
    doc_id = make_doc(client)
    aid = make_annotation(client, doc_id)
    response = client.request("DELETE", f"/annotations/{aid}")
    assert response.status_code == 200
    assert response.content == b""
    assert json.loads(response.headers["HX-Trigger"]) == {
        "annotation:deleted": {"id": aid}
    }
    assert aid not in client.get(f"/documents/{doc_id}/annotations").text


# Revisions


def test_snapshot_revision(client: TestClient) -> None:
    doc_id = make_doc(client)
    client.put(f"/documents/{doc_id}/content", json={"content": doc_with("First")})
    make_annotation(client, doc_id)
    response = client.post(
        f"/documents/{doc_id}/revisions", data={"label": "First pass", "is_major": "1"}
    )
    assert response.status_code == 200
    assert "First pass" in response.text
    assert "MAJOR" in response.text


def test_snapshot_stores_content_and_annotations(client: TestClient, tmp_path) -> None:
    doc_id = make_doc(client)
    client.put(f"/documents/{doc_id}/content", json={"content": doc_with("Snapshot me")})
    aid = make_annotation(client, doc_id)
    client.post(f"/documents/{doc_id}/revisions", data={"label": "keep"})

    conn = get_conn(tmp_path / "test.db")
    row = conn.execute(
        "SELECT * FROM revisions WHERE document_id = ?", (doc_id,)
    ).fetchone()
    conn.close()
    assert json.loads(row["content"]) == doc_with("Snapshot me")
    assert [a["id"] for a in json.loads(row["annotations"])] == [aid]


def test_flag_major(client: TestClient) -> None:
    doc_id = make_doc(client)
    client.post(f"/documents/{doc_id}/revisions", data={"label": "plain"})
    rid = revision_ids(client, doc_id)[0]

    flagged = client.post(
        f"/revisions/{rid}/flag", data={"is_major": "1", "label": "big one"}
    )
    assert flagged.status_code == 200
    assert "MAJOR" in flagged.text
    assert "big one" in flagged.text

    unflagged = client.post(
        f"/revisions/{rid}/flag", data={"is_major": "0", "label": "big one"}
    )
    assert "MAJOR" not in unflagged.text


def revision_ids(client: TestClient, doc_id: str) -> list[str]:
    """Return the revision ids of a document, newest first."""
    text = client.get(f"/documents/{doc_id}/revisions").text
    return [
        line.split('id="revision-')[1].split('"')[0]
        for line in text.splitlines()
        if 'id="revision-' in line
    ]


def test_revision_page_is_read_only(client: TestClient) -> None:
    doc_id = make_doc(client)
    client.put(f"/documents/{doc_id}/content", json={"content": doc_with("Old text")})
    client.post(f"/documents/{doc_id}/revisions", data={"label": "v1"})
    rid = revision_ids(client, doc_id)[0]

    response = client.get(f"/revisions/{rid}")
    assert response.status_code == 200
    assert "Old text" in response.text
    assert '"readOnly": true' in response.text
    assert "Read only" in response.text


def test_missing_revision_is_404(client: TestClient) -> None:
    assert client.get("/revisions/nope").status_code == 404
    assert client.post("/revisions/nope/restore").status_code == 404
    assert client.post("/revisions/nope/flag", data={"is_major": "1"}).status_code == 404


def test_restore_snapshots_then_copies_content(client: TestClient) -> None:
    doc_id = make_doc(client)
    client.put(f"/documents/{doc_id}/content", json={"content": doc_with("Version one")})
    client.post(f"/documents/{doc_id}/revisions", data={"label": "v1"})
    rid = revision_ids(client, doc_id)[0]

    client.put(f"/documents/{doc_id}/content", json={"content": doc_with("Version two")})

    response = client.post(f"/revisions/{rid}/restore")
    assert response.status_code == 200
    assert response.content == b""
    assert response.headers["HX-Redirect"] == f"/documents/{doc_id}"

    page = client.get(f"/documents/{doc_id}")
    assert "Version one" in page.text
    assert "Version two" not in page.text

    panel = client.get(f"/documents/{doc_id}/revisions").text
    assert "Before restore" in panel

    before = [
        r for r in revision_ids(client, doc_id) if r != rid
    ]
    assert len(before) == 1
    saved = client.get(f"/revisions/{before[0]}")
    assert "Version two" in saved.text
