from typing import Callable

import pandas as pd
import streamlit as st

from .backends.base import Backend

_SYSTEM_EVENTS = {"page_view", "session_start"}


def make_dashboard_page(backend: Backend) -> Callable[[], None]:
    """Return a Streamlit-compatible page function bound to the given backend.

    Usage in app.py:
        from streamlit_fyr.dashboard import make_dashboard_page
        st.Page(make_dashboard_page(backend), title="Page analytics", icon=":material/analytics:")
    """

    def _page() -> None:
        _render(backend)

    return _page


def _render(backend: Backend) -> None:
    try:
        import plotly.express as px
    except ImportError as e:
        raise ImportError(
            "make_dashboard_page requires plotly. "
            "Install with: pip install 'streamlit-fyr[dashboard]'"
        ) from e

    st.title(":material/analytics: Telemetry Dashboard")

    df = backend.query("SELECT * FROM events ORDER BY timestamp DESC")

    if df.empty:
        st.info("No telemetry data recorded yet.", icon=":material/info:")
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.date

    # ── Sidebar Filters ───────────────────────────────────────────────────────
    with st.sidebar:
        st.header(":material/filter_list: Filters")

        app_options = sorted(df["app_name"].unique().tolist())
        selected_apps = st.multiselect(
            "App",
            options=app_options,
            default=app_options,
            placeholder="All apps",
            key="tel_apps",
        )

        min_date = df["date"].min()
        max_date = df["date"].max()
        date_range = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="tel_date_range",
        )

    # ── Apply Filters ─────────────────────────────────────────────────────────
    filtered = df.copy()
    if selected_apps:
        filtered = filtered[filtered["app_name"].isin(selected_apps)]
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start, end = date_range
        filtered = filtered[(filtered["date"] >= start) & (filtered["date"] <= end)]

    if filtered.empty:
        st.info("No data for the current filters.", icon=":material/info:")
        return

    # ── Summary Metrics ───────────────────────────────────────────────────────
    session_durations = (
        filtered.groupby("session_id")["timestamp"]
        .agg(["min", "max"])
        .assign(duration_sec=lambda x: (x["max"] - x["min"]).dt.total_seconds())
    )
    avg_duration_sec = session_durations["duration_sec"].mean()
    avg_duration = (
        (
            f"{avg_duration_sec / 60:.1f} min"
            if avg_duration_sec >= 60
            else f"{avg_duration_sec:.0f} s"
        )
        if not pd.isna(avg_duration_sec)
        else "—"
    )

    unique_visitors = (
        filtered["visitor_id"].nunique() if "visitor_id" in filtered.columns else "—"
    )

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Total Events", len(filtered))
    m2.metric("Sessions", filtered["session_id"].nunique())
    m3.metric("Unique Visitors", unique_visitors)
    m4.metric("Avg Session Duration", avg_duration)
    m5.metric("Apps", filtered["app_name"].nunique())
    m6.metric(
        "Pages tracked",
        filtered.loc[filtered["page"].notna(), "page"].nunique(),
    )

    st.divider()

    # ── Sessions Over Time ────────────────────────────────────────────────────

    col_sessions_over_time, col_duration = st.columns(2)

    with col_sessions_over_time:
        st.subheader(":material/timeline: Sessions Over Time")
        sessions_daily = (
            filtered[filtered["event"] == "session_start"]
            .groupby(["date", "app_name"])
            .agg(sessions=("session_id", "nunique"))
            .reset_index()
        )
        if sessions_daily.empty:
            st.caption("No session_start events in range.")
        else:
            fig = px.line(
                sessions_daily,
                x="date",
                y="sessions",
                color="app_name",
                markers=True,
            )
            fig.update_layout(
                margin=dict(t=10, b=40, l=0, r=0),
                height=260,
                legend_title_text="App",
            )
            st.plotly_chart(fig, width="stretch")

    # ── Session Duration Distribution ─────────────────────────────────────────
    with col_duration:
        st.subheader(":material/timer: Session Duration")
        plot_durations = session_durations[session_durations["duration_sec"] > 0].copy()
        if plot_durations.empty:
            st.caption("Not enough data yet — needs sessions with more than one event.")
        else:
            plot_durations["duration_min"] = plot_durations["duration_sec"] / 60
            fig = px.histogram(
                plot_durations,
                x="duration_min",
                nbins=20,
                labels={"duration_min": "Duration (min)"},
            )
            fig.update_layout(
                margin=dict(t=10, b=40, l=0, r=0),
                height=320,
                yaxis_title="Sessions",
            )
            st.plotly_chart(fig, width="stretch")

    st.divider()

    col_pages, col_events = st.columns(2)

    # ── Top Pages ─────────────────────────────────────────────────────────────
    with col_pages:
        st.subheader(":material/pages: Top Pages")
        page_counts = (
            filtered[filtered["event"] == "page_view"]
            .groupby(["app_name", "page"])
            .size()
            .reset_index(name="views")
            .sort_values("views", ascending=False)
            .head(10)
        )
        if page_counts.empty:
            st.caption("No page_view events in range.")
        else:
            fig = px.bar(
                page_counts,
                x="views",
                y="page",
                color="app_name",
                orientation="h",
                text="views",
            )
            fig.update_layout(
                margin=dict(t=10, b=20, l=0, r=0),
                height=320,
                yaxis_title=None,
                legend_title_text="App",
            )
            st.plotly_chart(fig, width="stretch")

    # ── Top Custom Events ──────────────────────────────────────────────────────
    with col_events:
        st.subheader(":material/touch_app: Top Events")
        event_counts = (
            filtered[~filtered["event"].isin(_SYSTEM_EVENTS)]
            .groupby(["app_name", "event"])
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
            .head(10)
        )
        if event_counts.empty:
            st.info("No custom events tracked yet.", icon=":material/info:")
        else:
            fig = px.bar(
                event_counts,
                x="count",
                y="event",
                color="app_name",
                orientation="h",
                text="count",
            )
            fig.update_layout(
                margin=dict(t=10, b=20, l=0, r=0),
                height=320,
                yaxis_title=None,
                legend_title_text="App",
            )
            st.plotly_chart(fig, width="stretch")

    st.divider()

    # ── Raw Events ────────────────────────────────────────────────────────────
    with st.expander(":material/table_rows: Raw events", expanded=False):
        st.dataframe(
            filtered[
                [
                    "timestamp",
                    "app_name",
                    "visitor_id",
                    "page",
                    "event",
                    "session_id",
                    "properties",
                ]
            ]
            .sort_values("timestamp", ascending=False)
            .reset_index(drop=True),
            width="stretch",
            height=400,
        )
