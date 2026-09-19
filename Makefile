.PHONY: setup build dev test

setup:
	uv sync
	npm install

build:
	npm run build

dev:
	uv run uvicorn app.main:app --reload --port 8000

test:
	uv run pytest -q
