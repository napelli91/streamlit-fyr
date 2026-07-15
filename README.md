# Streamlit Fyr

Streamlit Fyr is a simple analytics package meant for being used as a "centralized"
analytics platform for multi-app streamlit deployments.

This package takes inspiration from:

- [Streamlit-analytics](https://github.com/jrieke/streamlit-analytics/tree/main)
- [Stremlit-page-analytics](https://github.com/Snowflake-Labs/streamlit-page-analytics/blob/main/pyproject.toml)

This package offers a simple SQLite backend to test out the capabilities of the
package, but the central usage is to connect to an external PostgresSQL and
connect multiple applications to a single DB in order to centralize page analytics.

Key features:

- Cookie-based persistent `visitor_id` across sessions.
- Per-event rows in a queryable relational DB.
- Multi-app centralization via `app_name` column. One DB for all your Streamlit apps
- Bundled Plotly dashboard page (`make_dashboard_page`)

## Installation

```bash
pip install streamlit-fyr               # core: Tracker + SQLiteBackend + raw query()
pip install 'streamlit-fyr[dashboard]'  # adds plotly for make_dashboard_page
pip install 'streamlit-fyr[postgres]'   # adds psycopg driver for PostgresBackend
pip install 'streamlit-fyr[all]'        # everything
```

The core install only ships SQLAlchemy + pandas + Streamlit. `plotly` and `psycopg`
are optional extras — install them only if you need the bundled dashboard or the
Postgres backend.

## Basic Usage

### SQLite backend

To test the capabilities of this package we recommend using first `SQLiteBackend`.
This backend will expect to receive a file name for the sqlite db file to be created.
Alternatively you can set the envrionmental variable `ST_FYR_SQLITE_FILE` to
your db file.

```python
import streamlit as st

from constants import DATA_PATH
from streamlit_fyr.dashboard import make_dashboard_page
from streamlit_fyr import SQLiteBackend, Tracker

backend = SQLiteBackend("telemetry.db")
tracker = Tracker(app_name="my_st_app", backend=backend)

tracker.init()

def my_page() -> None:
    """Render a new page."""
    tracker.page("my_page")
    st.title("My streamlit Page!")
    count = 0
    if st.button("click me!"):
        tracker.event("button_pressed", {"press_count": count})
        count += 1

...

page_telemetry = st.Page(
    make_dashboard_page(backend),
    title="Telemetry",
    icon=":material/analytics:",
)

pg = st.navigation({
        "App": [my_page],
        "Page Analytics": [page_telemetry],
    })
pg.run()
```

### Postgres backend

To enable the postgres backend you must change backend to the `PostgresBackend`
and add your DB connection string. Alternatively you can set the environment
variable `ST_FYR_CONNECTION_STRING` to your connection string and the backend
will read that value.

```python
from streamlit_fyr import PostgresBackend, Tracker

@st.cache_resource
def get_backend():
    return PostgresBackend(connection_string="postgresql+psycopg://...")

backend = get_backend()
tracker = Tracker(app_name="my_st_app", backend=backend)

## Same config as with SQLite
```

> [!IMPORTANT]
> **Do not construct it at module scope.** Cache the backend using `@st.cache_resource`.
> Streamlit re-executes the entire script on every interaction (button click, slider
> drag, etc.). `PostgresBackend(...)` calls `create_engine(...)`, which builds
> a new connection pool. Constructing it at module scope therefore leaks a new
> pool on every rerun and can quickly exhaust Postgres `max_connections`
> (`FATAL: too many connections`) even though your actual insert volume is
> tiny.

`PostgresBackend` forwards connection-pool settings to SQLAlchemy with sane
defaults (`pool_size=5`, `max_overflow=5`, `pool_pre_ping=True`); override them
(or pass any other `create_engine` kwarg) if you need to tune the pool:

```python
PostgresBackend(
    connection_string="postgresql+psycopg://...",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)
```

## Identifying authenticated users

If your app has authentication, call `tracker.identify()` after login resolves
to attach a known identity to all subsequent events in the session:

```python
user = get_logged_in_user()  # your auth layer
tracker.identify(user.id)
```

`identify()` stores the value in Streamlit session state and writes it to every
event from that point forward alongside `visitor_id`. Events fired before
`identify()` is called (e.g. the login page itself) will have `user_id = NULL`.

> [!IMPORTANT]
> **Privacy note:** `user_id` is stored as plain text in the `events` table.
> Prefer an opaque internal ID over an email address or display name. If you do
> store PII, ensure your database access controls and data retention policy
> reflect that obligation.

## Observing write failures

By design, **telemetry failures never break the host app** — if a backend write
fails, `Tracker` swallows the exception and continues. To avoid silently
dropping events with no signal, the library logs a full warning on the first
write failure per process (subsequent failures are logged at `debug`) via the
`streamlit_fyr` logger.

For a louder, actionable signal, pass an `on_write_error` callback. It is
invoked with the exception whenever a write fails, so you can surface or alert
on the failure without the library re-raising into your app:

```python
def alert(exc: Exception) -> None:
    my_error_reporter.capture(exc)  # e.g. Sentry, a metric, a log

tracker = Tracker(app_name="my_st_app", backend=backend, on_write_error=alert)
```

The callback must not raise; if it does, its exception is logged and suppressed
so the guarantee that telemetry cannot break the host app still holds.
