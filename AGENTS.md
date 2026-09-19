# Agent guide

This file is for coding agents that change this repository. For the writing
coach that runs editing passes through MCP, the server sends its own
instructions from `app/coach.py`.

## What this project is

A local web app for workshopping prose. A writer keeps documents in a
Notion-style editor. An agent runs editing passes over a document through an
MCP server and submits findings. A finding names a problem with a verbatim
quote, a paragraph number, and a note. The writer rewrites by hand and accepts
or rejects each finding in the sidebar.

Read the specs before you change behaviour:

- `docs/superpowers/specs/2026-09-19-workshop-bones-design.md`
- `docs/superpowers/specs/2026-09-19-editing-passes-mcp-design.md`

## Commands

```sh
make setup        # uv sync and npm install
make build        # build CSS, JS, and copy htmx into app/static
make dev          # uvicorn with reload on http://127.0.0.1:8000
make test         # pytest
npm run check     # syntax check of assets/js and a dry esbuild bundle
npm run watch     # rebuild CSS and JS while you edit assets/
```

Run `make test` and `npm run check` before you report a change as done.
Built files under `app/static/` are not in git. Run `make build` after you
edit anything under `assets/`.

## Stack

Python 3.12+, FastAPI, Jinja2, stdlib `sqlite3`, htmx, Tailwind v4 (local
build), TipTap 3 bundled with esbuild, `mcp` 2.x. No CDN. No frontend
framework.

## Map

| Path | Owns |
| --- | --- |
| `app/main.py` | routes, HTMX partial responses, the `/mcp` route, lifespan |
| `app/db.py` | connections, migrations keyed on `PRAGMA user_version`, seeding |
| `app/repo.py` | all SQL; functions take a connection and return dicts |
| `app/text.py` | plain text and paragraph numbering |
| `app/coach.py` | the coach rules and steps the agent receives |
| `app/mcp_server.py` | MCP tools and prompts |
| `app/seed_passes.py` | the 30 seeded passes |
| `app/templates/` | Jinja2 pages and `partials/` for HTMX swaps |
| `assets/js/editor.js` | TipTap setup |
| `assets/js/annotation-mark.js` | the `annotation` mark: `id`, `kind`, `pass` |
| `assets/js/annotation-state.js` | decoration plugin for active, resolved, dimmed |
| `assets/js/anchor.js` | finds a quote and applies the mark |
| `assets/js/sidebar.js` | card layout, active state, prev and next |
| `assets/js/passes.js` | current pass, filter, panel |
| `assets/js/changes.js` | polling and anchoring of new findings |
| `tests/` | pytest; `conftest.py` gives a temp database and fake passes |

## Rules that keep the system correct

**The browser is the only writer of document content.** The server never
edits a document's TipTap JSON. Findings arrive unanchored. The open browser
tab anchors them, applies the marks, and autosaves. If you need the server to
change content, stop and rethink.

**Never toggle classes on mark elements from JavaScript.** ProseMirror watches
DOM mutations inside the editor. It redraws any mark that changed behind its
back, and the redraw wipes the classes. Paint state through the decoration
plugin in `annotation-state.js`.

**Paragraph numbering must match on both sides.** `app/text.py` and
`assets/js/anchor.js` implement one rule. One number per top-level block.
One number per `listItem`. A `hardBreak` is a space. Empty blocks keep their
number. Change both files together and update `tests/test_text.py`.

**A finding never carries replacement wording.** The `submit_findings` schema
has `quote`, `paragraph`, and `note`. Do not add a field for a fix. The coach
text in `app/coach.py` states the same rule for the model.

**Schema changes are migrations.** `app/schema.sql` stays the version 1
schema. Add a numbered step in `app/db.py` and a test in
`tests/test_migration.py`. SQLite cannot alter a CHECK constraint; recreate
the table and copy the rows.

**Bump `change_seq`.** Any write to a document's annotations or runs must
call the repo helper that increments `documents.change_seq`. The browser polls
this value.

## MCP details

- `mcp` 2.x: `from mcp.server.mcpserver import MCPServer`. Tools are plain
  sync functions with type hints; each opens its own connection.
- The parameter is `pass_ref`, not `pass`. `pass` is a Python keyword and a
  pydantic alias breaks dispatch.
- `/mcp` is a Starlette `Route`, not a `Mount`. A mount answers only `/mcp/`
  and redirects, which some clients do not follow.
- The FastAPI lifespan enters `session_manager.run()`. The session manager is
  rebuilt on each startup because a manager runs once.
- The SDK turns on DNS rebinding protection for `127.0.0.1`. Clients must use
  `127.0.0.1` or `localhost` with the port.

## HTMX conventions

- Routes that swap return a partial from `app/templates/partials/`.
- Redirects set the `HX-Redirect` header and return 200 with an empty body.
- Events the JavaScript listens for arrive in `HX-Trigger`:
  `annotation:deleted` and `annotation:closed`, each with `{"id": ...}`.
- The specs list the DOM ids the JavaScript needs. Keep them.

## Style

- Type hints and small functions. JSDoc or a docstring on a function says
  what it does, never how.
- Comments elsewhere explain why, only when the code cannot.
- Prose in docs, commits, and PRs follows Simplified Technical English:
  short sentences, active voice, one name per thing.
- Commits use Conventional Commits: `feat:`, `fix:`, `chore:`.

## Debugging in the browser

The document page exposes the editor as `window.workshopEditor`. Use it from
the console or from a Playwright session to set selections, read
`state.doc`, or run commands.
