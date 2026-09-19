# Writing workshop tool

A local web app for workshopping prose. Each document has a rich text editor,
highlights with annotations in a sidebar, and revisions you can restore.

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

## Test

```sh
make test
```

## Layout

- `app/main.py` — FastAPI app and routes
- `app/db.py` — connections and schema setup
- `app/repo.py` — all SQL
- `app/schema.sql` — tables
- `app/templates/` — Jinja2 templates
- `assets/` — Tailwind and JavaScript sources
- `app/static/` — built CSS, JS, and vendored htmx
- `npm run watch` rebuilds CSS and JS while you edit `assets/`.
