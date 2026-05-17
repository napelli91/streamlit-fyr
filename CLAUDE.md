# CLAUDE.md

Guidance for Claude Code when working in this repository.

**Canonical doc is [AGENTS.md](AGENTS.md)** — architecture, event schema, implementation
notes, current state, known issues, and design decisions live there. Read it first.

## Quick orientation

`streamlit-fyr` is a lightweight, opt-in event-tracking library for Streamlit apps.
Named events (`tracker.event("filter_applied", {...})`) over auto-instrumented widgets.

## Tooling

- `uv sync` — install dev deps
- `uv run pytest` — run tests (single test: `uv run pytest tests/test_tracker.py::test_name`)
- `uv run black .` and `uv run isort .` — format / sort imports

Python >= 3.10. No CI; no lint config beyond black/isort.

## Working-on-this-repo rules

- Don't "simplify" `tracker.py:_resolve_visitor_id` without reading the cookie-lifecycle
  note in AGENTS.md — the render-counter pattern is load-bearing.
- `Tracker._write` swallows backend exceptions by design. Don't remove the `try/except`
  or re-raise — telemetry failures must not break the host app.
- New backends only need to implement `Backend.write()` and `Backend.query()`. Subclass
  `SQLAlchemyBackend` to get the ORM model + ad-hoc migration for free.
- Top-level package exports: `Tracker`, `SQLiteBackend`, `PostgresBackend`,
  `make_dashboard_page`. Keep `__init__.py` and the README in sync.
- Env-var fallbacks: `ST_FYR_SQLITE_FILE`, `ST_FYR_CONNECTION_STRING`.

For anything deeper (current state, known issues, immediate priorities, design history),
defer to [AGENTS.md](AGENTS.md).
