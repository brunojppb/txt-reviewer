# Writing workshop tool

A local web app for workshopping prose. Each document has a rich text editor,
highlights with annotations in a sidebar, and revisions you can restore. An
agent runs editing passes over a document through MCP and submits findings.

## Setup

```sh
make setup   # uv sync and npm install
make build   # build the CSS, the JS bundle, and copy htmx
```

## Run

```sh
make dev     # http://127.0.0.1:8000
```

The database lives at `data/app.db`. Set `WORKSHOP_DB` to use another path.
The app creates the tables at startup.

## Editing passes over MCP

The app serves an MCP server at `http://127.0.0.1:8000/mcp` while `make dev`
runs. A pass is one editing lens with a prompt. A run is one pass over one
document. A finding names a problem in the writer's own words; it never
proposes wording.

The repository holds a project `.mcp.json`, so Claude Code finds the server in
this directory. To add it for every directory:

```sh
claude mcp add --transport http --scope user workshop http://127.0.0.1:8000/mcp
```

Slash commands in Claude Code:

- `/mcp__workshop__run_pass` — run one pass over one document
- `/mcp__workshop__review` — run every enabled pass, one run each

Tools: `list_documents`, `get_document`, `list_passes`, `get_pass`,
`start_run`, `submit_findings`, `finish_run`, `list_findings`,
`snapshot_revision`.

Edit the passes at `/passes`. The seeded passes land at first start.

## Test

```sh
make test
```

## Layout

- `app/main.py` — FastAPI app and routes
- `app/db.py` — connections and schema setup
- `app/repo.py` — all SQL
- `app/text.py` — plain text and paragraph numbering
- `app/coach.py` — the coach text the agent reads
- `app/mcp_server.py` — the MCP tools and prompts
- `app/schema.sql` — tables
- `app/templates/` — Jinja2 templates
- `assets/` — Tailwind and JavaScript sources
- `app/static/` — built CSS, JS, and vendored htmx
- `npm run watch` rebuilds CSS and JS while you edit `assets/`.
