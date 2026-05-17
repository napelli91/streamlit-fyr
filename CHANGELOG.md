# Changelog

All notable changes to `streamlit-fyr` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `__init__.py` now exports `SQLiteBackend`, `PostgresBackend`,
  `make_dashboard_page`, and `__version__` at the top level.
- Environment-variable fallbacks for both backends: `ST_FYR_SQLITE_FILE`
  and `ST_FYR_CONNECTION_STRING`.
- Optional install extras: `[dashboard]` (plotly) and `[postgres]` (psycopg).
  Core install now ships only SQLAlchemy + pandas + Streamlit +
  extra-streamlit-components.
- PEP 561 `py.typed` marker — type hints are now visible to mypy / pyright in
  consumer projects.
- Strict `mypy` configuration and `pandas-stubs` dev dep.
- `[project.urls]`, classifiers, keywords, and SPDX license metadata in
  `pyproject.toml`.
- GitHub issue forms (bug / feature) and pull request template.

### Changed

- `Tracker._write` now swallows backend exceptions and logs via the
  `streamlit_fyr` logger. Telemetry failures no longer break the host app.
- `Tracker._write` drops events fired before `visitor_id` resolves (e.g. before
  `init()` completes). `session_id` is now nullable to reflect this.
- Cookie-load workaround in `Tracker._resolve_visitor_id` replaced the sticky
  `_visitor_cookie_checked` flag with a render counter
  (`_visitor_cookie_checks`, default 2 renders).
- `PostgresBackend()` raises a clear `ValueError` when neither an argument nor
  `ST_FYR_CONNECTION_STRING` is provided.
- Type annotations tightened across the public API
  (`dict[str, Any]`, `tuple[Any, ...]`, `Callable[[], None]`, `Engine`).

### Fixed

- README typos and broken example code (`streamlity_fyr`, `tracker.track`,
  `PostgresSQLBackend`, `with st.button(...)`).

## [0.1.0] — unreleased

Initial development. No public releases yet.
