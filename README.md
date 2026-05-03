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

## Basic Usage

### SQLite backend

To test the capabilities of this package we recommend using first `SQLiteBackend`.
This backend will expect to receive a file name for the sqlite db file to be created.
Alternatively you can set the envrionmental variable `ST_FYR_SQLITE_FILE` to
your db file.

```python
import streamlit as st

from constants import DATA_PATH
from streamlity_fyr.dashboard import make_dashboard_page
from streamlity_fyr import SQLiteBackend, Tracker

backend = SQLiteBackend("telemetry.db")
tracker = Tracker(app_name="my_st_app", backend=backend)

tracker.init()

def my_page() -> None:
    """Render a new page."""
    tracker.page("my_page")
    st.title("My streamlit Page!")
    count=0
    with st.button('click me!'):
        tracker.track("button_pressed", {"press_count": count})
        count+=1

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

To enable the postgres backend you must change backed to the `PostgresSQLBackend`
and add your DB connection string. Alternatively you can set the envrionmental
variable `ST_FYR_CONNECTION_STRING` to your connection string and the backend
will read that value.

```python
from streamlity_fyr import PostgresSQLBackend, Tracker

backend = PostgresSQLBackend(connection_string="postgresql+psycopg://...")
tracker = Tracker(app_name="my_st_app", backend=backend)

## Same config as with SQLite
```
