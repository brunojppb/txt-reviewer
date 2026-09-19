"""FastAPI app and routes for the writing workshop tool."""

from __future__ import annotations

import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from app import repo, text
from app.db import db_path, get_db, init_db
from app.mcp_server import server as mcp_server

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

Conn = Annotated[sqlite3.Connection, Depends(get_db)]


class MCPEndpoint:
    """The ASGI endpoint of the MCP server. It serves the whole protocol."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await mcp_server.session_manager.asgi_app(scope, receive, send)


def build_mcp_transport() -> None:
    """Give the MCP server a session manager for the streamable HTTP transport."""
    mcp_server.streamable_http_app(
        streamable_http_path="/mcp", stateless_http=True, json_response=True
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Migrate the database and start the MCP session manager."""
    init_db(db_path())
    # A session manager runs once, so every startup builds a fresh one. The
    # endpoint above asks for the current one on each request.
    build_mcp_transport()
    async with mcp_server.session_manager.run():
        yield


app = FastAPI(lifespan=lifespan)
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static"), check_dir=False),
    name="static",
)
# A route, not a mount: the endpoint answers at exactly /mcp, where a mount
# would send clients to /mcp/ through a redirect.
app.router.routes.append(Route("/mcp", endpoint=MCPEndpoint()))


def ago(value: str | None) -> str:
    """Return how long ago an ISO 8601 time was, in words."""
    if not value:
        return ""
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return ""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    minutes = int((datetime.now(timezone.utc) - moment).total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} minute{'' if minutes == 1 else 's'} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'' if hours == 1 else 's'} ago"
    days = hours // 24
    return f"{days} day{'' if days == 1 else 's'} ago"


templates.env.filters["ago"] = ago


def parse_json(raw: str, fallback: Any) -> Any:
    """Parse stored JSON and fall back when the text is broken."""
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return fallback


def empty_doc() -> dict[str, Any]:
    """Return the content of an empty document."""
    return json.loads(repo.EMPTY_DOC)


def render(request: Request, name: str, context: dict[str, Any]) -> HTMLResponse:
    """Render a template with the request in context."""
    return templates.TemplateResponse(request, name, context)


def hx_redirect(url: str) -> Response:
    """Return an empty 200 that tells htmx to move the browser."""
    return Response(status_code=200, headers={"HX-Redirect": url})


def hx_trigger(name: str, detail: dict[str, Any]) -> Response:
    """Return an empty 200 that fires an htmx event in the browser."""
    trigger = json.dumps({name: detail})
    return Response(status_code=200, headers={"HX-Trigger": trigger})


def need_document(conn: sqlite3.Connection, doc_id: str) -> dict[str, Any]:
    """Return a document or raise 404."""
    doc = repo.get_document(conn, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    return doc


def need_annotation(conn: sqlite3.Connection, aid: str) -> dict[str, Any]:
    """Return an annotation or raise 404."""
    annotation = repo.get_annotation(conn, aid)
    if annotation is None:
        raise HTTPException(status_code=404, detail="annotation not found")
    return annotation


def need_revision(conn: sqlite3.Connection, rid: str) -> dict[str, Any]:
    """Return a revision or raise 404."""
    revision = repo.get_revision(conn, rid)
    if revision is None:
        raise HTTPException(status_code=404, detail="revision not found")
    return revision


def need_pass(conn: sqlite3.Connection, pid: str) -> dict[str, Any]:
    """Return a pass or raise 404."""
    found = repo.get_pass(conn, pid)
    if found is None:
        raise HTTPException(status_code=404, detail="pass not found")
    return found


def card(request: Request, annotation: dict[str, Any]) -> HTMLResponse:
    """Render one annotation card."""
    return render(
        request,
        "partials/annotation_card.html",
        {"a": annotation, "readonly": False},
    )


def revision_panel(
    request: Request, conn: sqlite3.Connection, doc_id: str
) -> HTMLResponse:
    """Render the revisions panel of a document."""
    return render(
        request,
        "partials/revision_list.html",
        {"document_id": doc_id, "revisions": repo.list_revisions(conn, doc_id)},
    )


def pass_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group passes by their group name, in order of first appearance."""
    groups: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = row["group_name"] or "Other"
        group = index.get(name)
        if group is None:
            group = {"name": name, "passes": []}
            index[name] = group
            groups.append(group)
        group["passes"].append(row)
    return groups


def pass_list(request: Request, conn: sqlite3.Connection) -> HTMLResponse:
    """Render the pass list of the passes page."""
    return render(
        request,
        "partials/pass_list.html",
        {"groups": pass_groups(repo.list_passes(conn))},
    )


# Documents


@app.get("/", response_class=HTMLResponse)
def index(request: Request, conn: Conn) -> HTMLResponse:
    """Show every document, most recently updated first."""
    documents = repo.list_documents(conn)
    for doc in documents:
        doc["word_count"] = text.document_word_count(doc["content"])
    return render(request, "index.html", {"documents": documents})


@app.post("/documents")
def create_document(conn: Conn) -> Response:
    """Create a document and send the browser to its editor."""
    doc = repo.create_document(conn)
    return hx_redirect(f"/documents/{doc['id']}")


@app.get("/documents/{doc_id}", response_class=HTMLResponse)
def document_page(request: Request, doc_id: str, conn: Conn) -> HTMLResponse:
    """Show the editor page of one document."""
    doc = need_document(conn, doc_id)
    content = parse_json(doc["content"], empty_doc())
    doc_data = {
        "id": doc["id"],
        "title": doc["title"],
        "content": content,
        "readOnly": False,
    }
    return render(
        request,
        "document.html",
        {
            "doc": doc,
            "doc_data": doc_data,
            "annotations": repo.list_annotations(conn, doc_id, open_only=True),
            "closed_ids": repo.closed_annotation_ids(conn, doc_id),
            "passes": repo.list_passes(conn, enabled_only=True),
            "word_count": text.document_word_count(content),
        },
    )


@app.post("/documents/{doc_id}/title", response_class=HTMLResponse)
def set_title(
    request: Request,
    doc_id: str,
    conn: Conn,
    title: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Rename a document."""
    doc = repo.update_title(conn, doc_id, title.strip())
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    return render(request, "partials/title.html", {"doc": doc})


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str, conn: Conn) -> Response:
    """Delete a document and send the browser to the list."""
    if not repo.delete_document(conn, doc_id):
        raise HTTPException(status_code=404, detail="document not found")
    return hx_redirect("/")


@app.put("/documents/{doc_id}/content")
async def save_content(request: Request, doc_id: str, conn: Conn) -> JSONResponse:
    """Store the editor content of a document."""
    need_document(conn, doc_id)
    try:
        payload = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="body is not JSON")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="body is not an object")
    content = payload.get("content")
    if not isinstance(content, dict) or content.get("type") != "doc":
        raise HTTPException(status_code=400, detail="content is not a doc")
    updated_at = repo.update_content(conn, doc_id, content)
    if updated_at is None:
        raise HTTPException(status_code=404, detail="document not found")
    return JSONResponse({"ok": True, "updated_at": updated_at})


@app.get("/documents/{doc_id}/changes")
def document_changes(doc_id: str, conn: Conn) -> JSONResponse:
    """Report the change counter the browser polls."""
    need_document(conn, doc_id)
    return JSONResponse({"seq": repo.change_seq(conn, doc_id)})


# Annotations


@app.get("/documents/{doc_id}/annotations", response_class=HTMLResponse)
def annotation_list(
    request: Request, doc_id: str, conn: Conn, status: str = "open"
) -> HTMLResponse:
    """Show the annotation cards of a document. Open ones unless status is all."""
    need_document(conn, doc_id)
    annotations = repo.list_annotations(conn, doc_id, open_only=status != "all")
    return render(
        request,
        "partials/annotation_list.html",
        {
            "annotations": annotations,
            "closed_ids": repo.closed_annotation_ids(conn, doc_id),
            "readonly": False,
        },
    )


@app.post("/documents/{doc_id}/annotations", response_class=HTMLResponse)
def create_annotation(
    request: Request,
    doc_id: str,
    conn: Conn,
    id: Annotated[str, Form()],
    kind: Annotated[str, Form()],
) -> HTMLResponse:
    """Create an empty annotation for a highlight."""
    need_document(conn, doc_id)
    if kind not in repo.KINDS:
        raise HTTPException(status_code=400, detail="unknown kind")
    annotation = repo.create_annotation(conn, doc_id, id, kind)
    if annotation is None:
        raise HTTPException(status_code=409, detail="annotation id already exists")
    repo.bump_change_seq(conn, doc_id)
    return card(request, annotation)


@app.put("/annotations/{aid}", response_class=HTMLResponse)
def set_annotation_body(
    request: Request,
    aid: str,
    conn: Conn,
    body: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Store the text of an annotation."""
    need_annotation(conn, aid)
    annotation = repo.update_annotation_body(conn, aid, body)
    if annotation is None:
        raise HTTPException(status_code=404, detail="annotation not found")
    repo.bump_change_seq(conn, annotation["document_id"])
    return card(request, annotation)


@app.post("/annotations/{aid}/status")
def set_annotation_status(
    request: Request,
    aid: str,
    conn: Conn,
    status: Annotated[str, Form()],
) -> Response:
    """Open, accept, or reject an annotation."""
    need_annotation(conn, aid)
    if status not in repo.STATUSES:
        raise HTTPException(status_code=400, detail="unknown status")
    annotation = repo.set_annotation_status(conn, aid, status)
    if annotation is None:
        raise HTTPException(status_code=404, detail="annotation not found")
    repo.bump_change_seq(conn, annotation["document_id"])
    if status in repo.CLOSED_STATUSES:
        return hx_trigger("annotation:closed", {"id": aid})
    return card(request, annotation)


@app.post("/annotations/{aid}/anchored")
def set_annotation_anchored(
    aid: str,
    conn: Conn,
    anchored: Annotated[str, Form()] = "1",
) -> Response:
    """Record whether the browser put the highlight of a finding in the text."""
    need_annotation(conn, aid)
    repo.set_anchored(conn, aid, anchored not in ("", "0", "false", "off"))
    return Response(status_code=200)


@app.delete("/annotations/{aid}")
def delete_annotation(aid: str, conn: Conn) -> Response:
    """Delete an annotation and tell the editor to drop its mark."""
    annotation = need_annotation(conn, aid)
    if not repo.delete_annotation(conn, aid):
        raise HTTPException(status_code=404, detail="annotation not found")
    repo.bump_change_seq(conn, annotation["document_id"])
    return hx_trigger("annotation:deleted", {"id": aid})


@app.get("/documents/{doc_id}/findings/unanchored")
def unanchored_findings(doc_id: str, conn: Conn) -> JSONResponse:
    """List the open findings that wait for a highlight."""
    need_document(conn, doc_id)
    return JSONResponse(repo.list_unanchored_findings(conn, doc_id))


# Passes


@app.get("/passes", response_class=HTMLResponse)
def passes_page(request: Request, conn: Conn) -> HTMLResponse:
    """Show the editor for the editing passes."""
    return render(
        request, "passes.html", {"groups": pass_groups(repo.list_passes(conn))}
    )


@app.post("/passes", response_class=HTMLResponse)
def create_pass(
    request: Request,
    conn: Conn,
    title: Annotated[str, Form()] = "",
    group_name: Annotated[str, Form()] = "",
    prompt: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Add a pass at the end of the list."""
    repo.create_pass(conn, title.strip(), group_name.strip(), prompt.strip())
    return pass_list(request, conn)


@app.put("/passes/{pid}", response_class=HTMLResponse)
def update_pass(
    request: Request,
    pid: str,
    conn: Conn,
    title: Annotated[str, Form()] = "",
    group_name: Annotated[str, Form()] = "",
    prompt: Annotated[str, Form()] = "",
    enabled: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """Store the fields of one pass."""
    need_pass(conn, pid)
    row = repo.update_pass(
        conn,
        pid,
        title.strip(),
        group_name.strip(),
        prompt.strip(),
        enabled not in (None, "", "0", "false", "off"),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="pass not found")
    return render(request, "partials/pass_row.html", {"p": row})


@app.post("/passes/{pid}/move", response_class=HTMLResponse)
def move_pass(
    request: Request,
    pid: str,
    conn: Conn,
    direction: Annotated[str, Form()] = "up",
) -> HTMLResponse:
    """Move a pass one place up or down."""
    need_pass(conn, pid)
    if direction not in ("up", "down"):
        raise HTTPException(status_code=400, detail="unknown direction")
    repo.move_pass(conn, pid, direction)
    return pass_list(request, conn)


@app.delete("/passes/{pid}", response_class=HTMLResponse)
def delete_pass(request: Request, pid: str, conn: Conn) -> HTMLResponse:
    """Delete one pass."""
    need_pass(conn, pid)
    repo.delete_pass(conn, pid)
    return pass_list(request, conn)


@app.get("/documents/{doc_id}/passes-panel", response_class=HTMLResponse)
def passes_panel(request: Request, doc_id: str, conn: Conn) -> HTMLResponse:
    """Show which passes ran over a document and what they found."""
    need_document(conn, doc_id)
    status = repo.pass_status(conn, doc_id)
    rows = []
    for row in repo.list_passes(conn, enabled_only=True):
        counts = status.get(row["id"], {})
        rows.append(
            {
                **row,
                "done": bool(counts.get("done")),
                "open": counts.get("open", 0),
                "accepted": counts.get("accepted", 0),
                "last_finished": counts.get("last_finished"),
            }
        )
    return render(
        request,
        "partials/passes_panel.html",
        {
            "document_id": doc_id,
            "groups": pass_groups(rows),
            "pass_count": len(rows),
            "run_count": sum(1 for row in rows if row["done"]),
        },
    )


# Revisions


@app.get("/documents/{doc_id}/revisions", response_class=HTMLResponse)
def revision_list(request: Request, doc_id: str, conn: Conn) -> HTMLResponse:
    """Show the revisions panel of a document."""
    need_document(conn, doc_id)
    return revision_panel(request, conn, doc_id)


@app.post("/documents/{doc_id}/revisions", response_class=HTMLResponse)
def create_revision(
    request: Request,
    doc_id: str,
    conn: Conn,
    label: Annotated[str, Form()] = "",
    is_major: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """Snapshot the content and annotations of a document."""
    need_document(conn, doc_id)
    major = is_major not in (None, "", "0", "false", "off")
    if repo.create_revision(conn, doc_id, label.strip(), major) is None:
        raise HTTPException(status_code=404, detail="document not found")
    return revision_panel(request, conn, doc_id)


@app.post("/revisions/{rid}/flag", response_class=HTMLResponse)
def flag_revision(
    request: Request,
    rid: str,
    conn: Conn,
    is_major: Annotated[str, Form()] = "0",
    label: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Set the major flag and label of a revision."""
    revision = need_revision(conn, rid)
    major = is_major not in ("", "0", "false", "off")
    repo.flag_revision(conn, rid, major, label.strip())
    return revision_panel(request, conn, revision["document_id"])


@app.get("/revisions/{rid}", response_class=HTMLResponse)
def revision_page(request: Request, rid: str, conn: Conn) -> HTMLResponse:
    """Show one revision, read only."""
    revision = need_revision(conn, rid)
    doc = need_document(conn, revision["document_id"])
    annotations = parse_json(revision["annotations"], [])
    if not isinstance(annotations, list):
        annotations = []
    doc_data = {
        "id": doc["id"],
        "title": doc["title"],
        "content": parse_json(revision["content"], empty_doc()),
        "readOnly": True,
    }
    return render(
        request,
        "revision.html",
        {
            "doc": doc,
            "revision": revision,
            "doc_data": doc_data,
            "annotations": annotations,
        },
    )


@app.post("/revisions/{rid}/restore")
def restore_revision(rid: str, conn: Conn) -> Response:
    """Snapshot the document, then put the revision content back."""
    need_revision(conn, rid)
    doc = repo.restore_revision(conn, rid)
    if doc is None:
        raise HTTPException(status_code=404, detail="revision not found")
    return hx_redirect(f"/documents/{doc['id']}")
