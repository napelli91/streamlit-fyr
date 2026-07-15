# Changelog

All notable changes to `streamlit-fyr` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] — 2026-07-15

Schema provisioning is now explicit, the `events` table is indexed, and
`Backend.query` takes named parameters. Pre-1.0 — if you run Postgres, read the
behavior-change note under Changed.

### Added

- `SQLAlchemyBackend.ensure_schema()` — idempotent schema provisioning
  (`create_all` + `user_id` backfill + index creation). Run once at deploy time
  with a privileged role.
- `ensure_schema` constructor flag on backends: `SQLiteBackend(..., ensure_schema=True)`
  (default — zero-config local/dev) and `PostgresBackend(..., ensure_schema=False)`
  (default — production; apps do no DDL and can run as INSERT-only roles).
- Indexes on the `events` table — `ix_events_app_name_timestamp` (composite,
  primary dashboard filter), `ix_events_user_id`, `ix_events_visitor_id`.
  Created via `ensure_schema()`, including on tables that predate them.

### Changed

- **Behavior change (Postgres).** `PostgresBackend` no longer runs DDL on every
  construction. Provision the schema once with `backend.ensure_schema()` (a
  DDL-capable role) before apps write, or pass `ensure_schema=True` to restore
  the previous behavior. SQLite is unchanged (auto-provisions by default).
- `Backend.query(sql, params)` now takes a named-parameter mapping
  (`Mapping[str, Any] | None`) instead of a positional tuple.

### Fixed

- `Backend.query` with parameters now works. The previous `tuple[Any, ...]`
  signature never worked with the `text()`-based implementation (it raised
  `DatabaseError`); named-mapping parameters bind correctly.

## [0.2.0] — 2026-05-17

First public release. Pre-1.0 — public API may still change in minor versions.

### Public API

- `Tracker(app_name, backend)` with `init()`, `page()`, `event()`, `identify()`.
- `SQLiteBackend(db_path=None)` — WAL mode on by default; falls back to the
  `ST_FYR_SQLITE_FILE` env var, then to `telemetry.db`.
- `PostgresBackend(connection_string=None)` — falls back to the
  `ST_FYR_CONNECTION_STRING` env var; raises `ValueError` if neither is set.
- `make_dashboard_page(backend)` — returns a zero-arg callable suitable for
  `st.Page(...)`. Renders sessions over time, session-duration histogram, top
  pages, top custom events, and a raw events table.
- All four symbols are exported from the top-level `streamlit_fyr` package.

### Packaging

- Optional install extras: `streamlit-fyr[dashboard]` (plotly) and
  `streamlit-fyr[postgres]` (psycopg). Core install ships only SQLAlchemy +
  pandas + Streamlit + extra-streamlit-components.
- PEP 561 `py.typed` marker — type hints are visible to mypy / pyright in
  consumer projects.
- SPDX license metadata, `[project.urls]`, classifiers, and keywords in
  `pyproject.toml`.

### Reliability

- `Tracker._write` swallows backend exceptions and logs via the
  `streamlit_fyr` logger — telemetry failures cannot break the host app.
- Events fired before `visitor_id` resolves (e.g. before `init()` completes)
  are dropped silently; `session_id` is nullable to reflect this.
- Cookie-load handling in `Tracker._resolve_visitor_id` uses a render counter
  (`_visitor_cookie_checks`, default 2 renders) so a returning visitor's cookie
  is never overwritten by a freshly minted UUID.

### Developer experience

- Strict `mypy` configuration and `pandas-stubs` dev dep.
- GitHub Actions: `ci.yml` (pytest matrix 3.10–3.13, black, isort, mypy) and
  `release.yml` (tag-driven build + GitHub Release + PyPI Trusted Publishing).
- Issue forms (bug / feature) and pull request template.
