"""Route tests against a temporary database."""

from __future__ import annotations

import json
import uuid

from fastapi.testclient import TestClient
from mcp_types import LATEST_PROTOCOL_VERSION

from app import repo
from app.db import get_conn
from tests.conftest import doc_with, make_annotation, make_doc

DOC = {"type": "doc", "content": [{"type": "paragraph"}]}


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


def test_accept_annotation_sends_trigger(client: TestClient) -> None:
    doc_id = make_doc(client)
    aid = make_annotation(client, doc_id)
    response = client.post(f"/annotations/{aid}/status", data={"status": "accepted"})
    assert response.status_code == 200
    assert response.content == b""
    assert json.loads(response.headers["HX-Trigger"]) == {
        "annotation:closed": {"id": aid}
    }


def test_reopen_annotation_returns_card(client: TestClient) -> None:
    doc_id = make_doc(client)
    aid = make_annotation(client, doc_id)
    client.post(f"/annotations/{aid}/status", data={"status": "rejected"})
    reopened = client.post(f"/annotations/{aid}/status", data={"status": "open"})
    assert reopened.status_code == 200
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


def test_snapshot_stores_content_and_annotations(client: TestClient, db_file) -> None:
    doc_id = make_doc(client)
    client.put(f"/documents/{doc_id}/content", json={"content": doc_with("Snapshot me")})
    aid = make_annotation(client, doc_id)
    client.post(f"/documents/{doc_id}/revisions", data={"label": "keep"})

    conn = get_conn(db_file)
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


# Passes


def test_passes_page_lists_passes(client: TestClient, fake_passes) -> None:
    response = client.get("/passes")
    assert response.status_code == 200
    assert "Cut filler" in response.text
    assert "Writing cleanup" in response.text
    assert 'data-slug="long-sentences"' in response.text


def test_create_pass(client: TestClient, fake_passes) -> None:
    response = client.post(
        "/passes",
        data={"title": "Weak verbs", "group_name": "Sentences", "prompt": "Find them."},
    )
    assert response.status_code == 200
    assert "Weak verbs" in response.text
    assert 'data-slug="weak-verbs"' in response.text


def test_update_pass(client: TestClient, conn, fake_passes) -> None:
    pid = fake_passes[0]["id"]
    response = client.put(
        f"/passes/{pid}",
        data={"title": "Filler", "group_name": "Cleanup", "prompt": "Find filler."},
    )
    assert response.status_code == 200
    assert "Filler" in response.text
    # The checkbox was absent, so the pass is off now.
    assert repo.get_pass(conn, pid)["enabled"] == 0


def test_move_pass(client: TestClient, conn, fake_passes) -> None:
    second = fake_passes[1]["id"]
    response = client.post(f"/passes/{second}/move", data={"direction": "up"})
    assert response.status_code == 200
    assert [p["slug"] for p in repo.list_passes(conn)] == [
        "long-sentences",
        "cut-filler",
    ]
    client.post(f"/passes/{second}/move", data={"direction": "down"})
    assert [p["slug"] for p in repo.list_passes(conn)] == [
        "cut-filler",
        "long-sentences",
    ]


def test_move_pass_bad_direction_is_400(client: TestClient, fake_passes) -> None:
    pid = fake_passes[0]["id"]
    assert client.post(f"/passes/{pid}/move", data={"direction": "sideways"}).status_code == 400


def test_delete_pass(client: TestClient, conn, fake_passes) -> None:
    pid = fake_passes[0]["id"]
    response = client.request("DELETE", f"/passes/{pid}")
    assert response.status_code == 200
    assert "Cut filler" not in response.text
    assert len(repo.list_passes(conn)) == 1


def test_pass_routes_404(client: TestClient) -> None:
    assert client.put("/passes/nope", data={"title": "x"}).status_code == 404
    assert client.post("/passes/nope/move", data={"direction": "up"}).status_code == 404
    assert client.request("DELETE", "/passes/nope").status_code == 404


def test_document_page_has_the_pass_toolbar(client: TestClient, fake_passes) -> None:
    doc_id = make_doc(client)
    page = client.get(f"/documents/{doc_id}").text
    assert 'id="pass-toolbar"' in page
    assert 'id="pass-select"' in page
    assert 'id="passes-panel"' in page
    assert 'id="word-count"' in page
    assert 'data-slug="cut-filler"' in page


def test_passes_panel_counts_runs(client: TestClient, conn, fake_passes) -> None:
    doc_id = make_doc(client)
    client.put(f"/documents/{doc_id}/content", json={"content": doc_with("The wind rose.")})
    first = fake_passes[0]
    run = repo.create_run(conn, doc_id, first["id"], "test")
    repo.create_finding(conn, doc_id, first["id"], run["id"], "wind", 1, "Vague.")
    repo.finish_run(conn, run["id"])

    response = client.get(f"/documents/{doc_id}/passes-panel")
    assert response.status_code == 200
    assert 'data-run-count="1"' in response.text
    assert 'data-pass-count="2"' in response.text
    assert "1 open · 0 accepted" in response.text
    assert f'data-pass-id="{first["id"]}"' in response.text


# Findings


def make_finding(conn, doc_id: str, quote: str = "wind", note: str = "Vague.") -> str:
    """Store one finding of one run and return its annotation id."""
    first = repo.list_passes(conn)[0]
    run = repo.create_run(conn, doc_id, first["id"], "test")
    finding = repo.create_finding(conn, doc_id, first["id"], run["id"], quote, 1, note)
    return finding["id"]


def test_changes_reports_the_counter(client: TestClient) -> None:
    doc_id = make_doc(client)
    assert client.get(f"/documents/{doc_id}/changes").json() == {"seq": 0}
    make_annotation(client, doc_id)
    assert client.get(f"/documents/{doc_id}/changes").json()["seq"] == 1
    assert client.get("/documents/nope/changes").status_code == 404


def test_unanchored_findings(client: TestClient, conn, fake_passes) -> None:
    doc_id = make_doc(client)
    aid = make_finding(conn, doc_id)
    response = client.get(f"/documents/{doc_id}/findings/unanchored")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == aid
    assert payload[0]["pass_slug"] == "cut-filler"
    assert payload[0]["quote"] == "wind"
    assert payload[0]["paragraph"] == 1


def test_anchored_drops_the_finding_from_the_list(client: TestClient, conn, fake_passes) -> None:
    doc_id = make_doc(client)
    aid = make_finding(conn, doc_id)
    response = client.post(f"/annotations/{aid}/anchored", data={"anchored": "1"})
    assert response.status_code == 200
    assert response.content == b""
    assert client.get(f"/documents/{doc_id}/findings/unanchored").json() == []
    assert client.post("/annotations/nope/anchored", data={"anchored": "1"}).status_code == 404


def test_finding_card_shows_the_pass_title(client: TestClient, conn, fake_passes) -> None:
    doc_id = make_doc(client)
    aid = make_finding(conn, doc_id, note="This word says nothing.")
    cards = client.get(f"/documents/{doc_id}/annotations").text
    assert f'data-annotation-id="{aid}"' in cards
    assert 'data-source="pass"' in cards
    assert 'data-pass-slug="cut-filler"' in cards
    assert "Cut filler" in cards
    assert "This word says nothing." in cards
    # The browser has not anchored it yet, so the card shows the quote.
    assert "wind" in cards


def test_annotation_list_shows_open_ones_only(client: TestClient) -> None:
    doc_id = make_doc(client)
    open_id = make_annotation(client, doc_id)
    closed_id = make_annotation(client, doc_id)
    client.post(f"/annotations/{closed_id}/status", data={"status": "accepted"})

    open_only = client.get(f"/documents/{doc_id}/annotations").text
    assert f'id="annotation-{open_id}"' in open_only
    assert f'id="annotation-{closed_id}"' not in open_only

    every = client.get(f"/documents/{doc_id}/annotations", params={"status": "all"}).text
    assert open_id in every
    assert closed_id in every


def test_annotation_list_names_closed_ids_for_the_sidebar(client: TestClient) -> None:
    doc_id = make_doc(client)
    open_id = make_annotation(client, doc_id)
    closed_id = make_annotation(client, doc_id)
    client.post(f"/annotations/{closed_id}/status", data={"status": "rejected"})

    html = client.get(f"/documents/{doc_id}/annotations").text
    assert f'data-closed-ids="{closed_id}"' in html
    assert open_id not in html.split("data-closed-ids=")[1].split('"')[1]

    page = client.get(f"/documents/{doc_id}").text
    assert f'data-closed-ids="{closed_id}"' in page


# MCP endpoint


def test_mcp_endpoint_answers_at_the_exact_path(client: TestClient) -> None:
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": LATEST_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        },
    }
    response = client.post(
        "/mcp",
        json=body,
        headers={"accept": "application/json, text/event-stream"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["serverInfo"]["name"] == "workshop"
    assert "stern writing coach" in payload["result"]["instructions"]


def test_mcp_endpoint_lists_the_tools(client: TestClient) -> None:
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        headers={"accept": "application/json, text/event-stream"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    tools = {tool["name"]: tool for tool in response.json()["result"]["tools"]}
    assert "submit_findings" in tools
    assert "start_run" in tools
    schema = tools["submit_findings"]["inputSchema"]["properties"]["findings"]
    assert schema["type"] == "array"


def test_mcp_endpoint_lists_the_prompts(client: TestClient) -> None:
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 3, "method": "prompts/list", "params": {}},
        headers={"accept": "application/json, text/event-stream"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    names = {p["name"] for p in response.json()["result"]["prompts"]}
    assert names == {"run_pass", "review"}
