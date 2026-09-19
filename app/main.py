"""FastAPI app and routes for the writing workshop tool."""

from __future__ import annotations

import json
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import repo
from app.db import db_path, get_db, init_db

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

Conn = Annotated[sqlite3.Connection, Depends(get_db)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the schema before the app serves any request."""
    init_db(db_path())
    yield


app = FastAPI(lifespan=lifespan)
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static"), check_dir=False),
    name="static",
)


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


# Documents


@app.get("/", response_class=HTMLResponse)
def index(request: Request, conn: Conn) -> HTMLResponse:
    """Show every document, most recently updated first."""
    return render(request, "index.html", {"documents": repo.list_documents(conn)})


@app.post("/documents")
def create_document(conn: Conn) -> Response:
    """Create a document and send the browser to its editor."""
    doc = repo.create_document(conn)
    return hx_redirect(f"/documents/{doc['id']}")


@app.get("/documents/{doc_id}", response_class=HTMLResponse)
def document_page(request: Request, doc_id: str, conn: Conn) -> HTMLResponse:
    """Show the editor page of one document."""
    doc = need_document(conn, doc_id)
    doc_data = {
        "id": doc["id"],
        "title": doc["title"],
        "content": parse_json(doc["content"], empty_doc()),
        "readOnly": False,
    }
    return render(
        request,
        "document.html",
        {
            "doc": doc,
            "doc_data": doc_data,
            "annotations": repo.list_annotations(conn, doc_id),
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


# Annotations


@app.get("/documents/{doc_id}/annotations", response_class=HTMLResponse)
def annotation_list(request: Request, doc_id: str, conn: Conn) -> HTMLResponse:
    """Show the annotation cards of a document."""
    need_document(conn, doc_id)
    return render(
        request,
        "partials/annotation_list.html",
        {"annotations": repo.list_annotations(conn, doc_id), "readonly": False},
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
    return card(request, annotation)


@app.post("/annotations/{aid}/status", response_class=HTMLResponse)
def set_annotation_status(
    request: Request,
    aid: str,
    conn: Conn,
    status: Annotated[str, Form()],
) -> HTMLResponse:
    """Open or resolve an annotation."""
    need_annotation(conn, aid)
    if status not in repo.STATUSES:
        raise HTTPException(status_code=400, detail="unknown status")
    annotation = repo.set_annotation_status(conn, aid, status)
    if annotation is None:
        raise HTTPException(status_code=404, detail="annotation not found")
    return card(request, annotation)


@app.delete("/annotations/{aid}")
def delete_annotation(aid: str, conn: Conn) -> Response:
    """Delete an annotation and tell the editor to drop its mark."""
    if not repo.delete_annotation(conn, aid):
        raise HTTPException(status_code=404, detail="annotation not found")
    trigger = json.dumps({"annotation:deleted": {"id": aid}})
    return Response(status_code=200, headers={"HX-Trigger": trigger})


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
