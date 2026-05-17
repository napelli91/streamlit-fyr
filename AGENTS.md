# AGENTS.md — streamlit-fyr

Canonical architecture / history doc. `CLAUDE.md` points here.

## What this is

`streamlit-fyr` is a lightweight, explicit event-tracking library for Streamlit apps.
"Fyr" means beacon/lighthouse in Swedish.

**Philosophy:** opt-in, named events (`tracker.event("filter_applied", {...})`) rather than
auto-instrumenting every widget. This gives semantic signal instead of noise, at the cost
of requiring manual call sites.

**Key differentiators over alternatives** (jrieke/streamlit-analytics,
Snowflake-Labs/streamlit-page-analytics):

- Cookie-based persistent `visitor_id` across sessions (neither competitor solves this)
- Per-event rows in a queryable relational DB (not just aggregated counts)
- Multi-app centralization via `app_name` column — one DB for all your Streamlit apps
- Optional `user_id` via `tracker.identify()` once auth resolves
- Bundled Plotly dashboard page (`make_dashboard_page`)

---

## Tooling / commands

Project uses `uv` (see `uv.lock`, `uv_build` backend in `pyproject.toml`).

- Install dev deps: `uv sync`
- Run tests: `uv run pytest`
- Run a single test: `uv run pytest tests/test_tracker.py::test_name`
- Format / sort imports: `uv run black .` and `uv run isort .`

Python >= 3.10. No lint config beyond black/isort; no CI in repo.

---

## Architecture

```bash
src/streamlit_fyr/
├── __init__.py          # exports Tracker, SQLiteBackend, PostgresBackend, make_dashboard_page
├── tracker.py           # Tracker — public API: init(), page(), event(), identify()
├── dashboard.py         # make_dashboard_page(backend) factory
└── backends/
    ├── base.py          # Backend ABC: write(event), query(sql) -> DataFrame
    ├── models.py        # SQLAlchemy Base, Event ORM model, SQLAlchemyBackend base
    ├── sqlite.py        # SQLiteBackend — engine + WAL mode via connect event listener
    └── postgres.py      # PostgresBackend — engine with QueuePool
```

### Event schema

| Column | Type | Notes |
|--------|------|-------|
| `id` | int | autoincrement |
| `timestamp` | ISO-8601 text | UTC |
| `session_id` | UUID text, nullable | generated once per browser session in `tracker.init()` |
| `visitor_id` | UUID text | persisted across sessions via cookie |
| `user_id` | text, nullable | set by `tracker.identify()`; opaque ID, not PII |
| `app_name` | text | set in `Tracker(app_name=...)` |
| `page` | text | set by `tracker.page(name)`, inherited by subsequent events |
| `event` | text | `session_start`, `page_view`, or any custom name |
| `properties` | JSON text | optional dict passed to `tracker.event()` |

### Important implementation notes

- `visitor_id` resolution uses `extra-streamlit-components` CookieManager and requires
  an async-load workaround — see `tracker.py:_resolve_visitor_id`. We count renders
  (`_visitor_cookie_checks`) and wait `_COOKIE_LOAD_RENDERS` (=2) renders before minting
  a fresh UUID, so we never overwrite a returning visitor's cookie. Don't "simplify"
  this without understanding the cookie lifecycle.
- `Tracker._write` is wrapped in `try/except` and logs via the `streamlit_fyr` logger.
  Telemetry failures must never break the host app.
- `_write` early-returns when `visitor_id` isn't in session state — events fired before
  the cookie resolves (or before `init()` runs) are dropped silently. `session_id` is
  nullable for the same reason.
- The `Backend` ABC + `SQLAlchemyBackend` base keep `Tracker` and `dashboard.py`
  storage-agnostic. A new backend only needs `write()` and `query()`.
- `make_dashboard_page(backend)` returns a zero-arg callable for `st.Page(...)` closing
  over the backend — avoids globals. The consumer app is responsible for gating dashboard
  access (e.g. `?analytics=1`); the library does not enforce this.
- Backends accept env-var fallbacks: `ST_FYR_SQLITE_FILE` and `ST_FYR_CONNECTION_STRING`.
  `PostgresBackend()` raises `ValueError` if neither the argument nor the env var is set.
- **Dependency layout:** `pandas` + `sqlalchemy` + `streamlit` + `extra-streamlit-components`
  are core. `plotly` lives under the `[dashboard]` extra and is imported lazily inside
  `dashboard._render` — `import streamlit_fyr` works without it. `psycopg` lives under
  the `[postgres]` extra; SQLAlchemy only needs it at connect time, so importing
  `PostgresBackend` works without it (only `__init__` would fail).

---

## Usage pattern (consumer app)

```python
from streamlit_fyr import Tracker, SQLiteBackend, make_dashboard_page
# or: from streamlit_fyr import PostgresBackend

backend = SQLiteBackend("telemetry.db")
tracker = Tracker(app_name="my_app", backend=backend)

# app.py — before pg.run()
tracker.init()

# each page file
def my_page():
    tracker.page("my_page")
    if st.button("Export"):
        tracker.event("export_clicked", {"format": "csv"})

# Register the built-in dashboard page
st.Page(make_dashboard_page(backend), title="Telemetry", icon=":material/analytics:")
```

Access the dashboard via `?analytics=1` query param (implement the guard in the
consumer app — `fyr` itself does not enforce this).

## Design decisions (do not revisit without reason)

- **Explicit events, not auto-instrumentation.** Auto-instrumenting `st.*` is possible
  (jrieke/streamlit-analytics does it) but produces undifferentiated widget-click noise.
  The explicit API gives semantic events that are easier to aggregate and query.
- **`visitor_id` via cookie, not IP/fingerprint.** The async-CookieManager pattern is
  awkward but privacy-safe and the only reliable cross-session identity available in
  Streamlit without a login wall.
- **`user_id` stored as plain text.** Docs warn consumers to use opaque IDs, not PII.
- **`Backend` ABC + pluggable implementations.** Keeps `Tracker` and `dashboard.py`
  storage-agnostic. Adding a new backend (Snowflake, DuckDB) only requires implementing
  `write()` and `query()`.
- **`make_dashboard_page` factory pattern.** Returns a zero-arg callable compatible with
  `st.Page(...)` while closing over the backend instance. Avoids globals.
- **Telemetry failures must not break the host app.** `_write` swallows exceptions and
  logs — by design.
