import json
import logging
from unittest.mock import patch

import pandas as pd
import pytest

from streamlit_fyr.backends.base import Backend
from streamlit_fyr.tracker import Tracker
from tests.conftest import FakeSessionState, MockBackend


@pytest.fixture
def tracker(session_state, mock_backend):
    t = Tracker(app_name="test_app", backend=mock_backend)
    return t, mock_backend, session_state


def test_write_produces_correct_schema(tracker):
    t, backend, session_state = tracker
    with patch("streamlit_fyr.tracker.st.session_state", session_state):
        t._write("test_event")

    row = backend.writes[0]
    assert row["event"] == "test_event"
    assert row["app_name"] == "test_app"
    assert row["session_id"] == "test-session-id"
    assert row["visitor_id"] == "test-visitor-id"
    assert row["user_id"] is None
    assert "timestamp" in row
    assert "properties" in row


def test_write_without_identify_has_null_user_id(tracker):
    t, backend, session_state = tracker
    with patch("streamlit_fyr.tracker.st.session_state", session_state):
        t._write("test_event")
    assert backend.writes[0]["user_id"] is None


def test_identify_attaches_user_id_to_subsequent_events(tracker):
    t, backend, session_state = tracker
    with patch("streamlit_fyr.tracker.st.session_state", session_state):
        t.identify("user-42")
        t._write("test_event")
    assert backend.writes[0]["user_id"] == "user-42"


def test_identify_does_not_affect_prior_events(tracker):
    t, backend, session_state = tracker
    with patch("streamlit_fyr.tracker.st.session_state", session_state):
        t._write("before_login")
        t.identify("user-42")
        t._write("after_login")
    assert backend.writes[0]["user_id"] is None
    assert backend.writes[1]["user_id"] == "user-42"


def test_page_fires_page_view_event(tracker):
    t, backend, session_state = tracker
    with patch("streamlit_fyr.tracker.st.session_state", session_state):
        t.page("dashboard")
    assert backend.writes[0]["event"] == "page_view"


def test_page_sets_current_page_in_session(tracker):
    t, backend, session_state = tracker
    with patch("streamlit_fyr.tracker.st.session_state", session_state):
        t.page("settings")
    assert session_state["_current_page"] == "settings"


def test_page_context_inherited_by_subsequent_event(tracker):
    t, backend, session_state = tracker
    with patch("streamlit_fyr.tracker.st.session_state", session_state):
        t.page("settings")
        t.event("form_submitted")
    # writes[0] = page_view, writes[1] = form_submitted
    assert backend.writes[1]["page"] == "settings"


def test_event_name_is_recorded(tracker):
    t, backend, session_state = tracker
    with patch("streamlit_fyr.tracker.st.session_state", session_state):
        t.event("button_clicked")
    assert backend.writes[0]["event"] == "button_clicked"


def test_event_properties_are_json_serialized(tracker):
    t, backend, session_state = tracker
    with patch("streamlit_fyr.tracker.st.session_state", session_state):
        t.event("filter_applied", {"column": "region", "value": "EU"})
    props = json.loads(backend.writes[0]["properties"])
    assert props == {"column": "region", "value": "EU"}


def test_event_without_properties_writes_empty_json(tracker):
    t, backend, session_state = tracker
    with patch("streamlit_fyr.tracker.st.session_state", session_state):
        t.event("something_happened")
    assert json.loads(backend.writes[0]["properties"]) == {}


def test_event_before_init_does_not_write(mock_backend):
    """Events fired before cookie resolves (no visitor_id) must be dropped silently."""
    t = Tracker(app_name="test_app", backend=mock_backend)
    empty_state = FakeSessionState()
    with patch("streamlit_fyr.tracker.st.session_state", empty_state):
        t.event("too_early")
    assert mock_backend.writes == []


class _RaisingBackend(Backend):
    def write(self, event: dict) -> None:
        raise RuntimeError("db is down")

    def query(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        return pd.DataFrame()


def test_write_swallows_backend_exceptions(session_state, caplog):
    """A failing backend must never propagate into the host app."""
    t = Tracker(app_name="test_app", backend=_RaisingBackend())
    with patch("streamlit_fyr.tracker.st.session_state", session_state):
        with caplog.at_level(logging.ERROR, logger="streamlit_fyr"):
            t.event("anything")  # must not raise
    assert any("failed to write event" in r.message for r in caplog.records)


# --- Issue #6: page() de-duplicates page_view across reruns -------------------


def test_page_repeated_same_page_emits_single_view(tracker):
    """Reruns of the same page (widget interactions) must not re-log page_view."""
    t, backend, session_state = tracker
    with patch("streamlit_fyr.tracker.st.session_state", session_state):
        t.page("Home")
        t.page("Home")
        t.page("Home")
    page_views = [w for w in backend.writes if w["event"] == "page_view"]
    assert len(page_views) == 1
    assert json.loads(page_views[0]["properties"])["page"] == "Home"


def test_page_switch_emits_new_view(tracker):
    """Navigating to a different page emits a fresh page_view."""
    t, backend, session_state = tracker
    with patch("streamlit_fyr.tracker.st.session_state", session_state):
        t.page("Home")
        t.page("Reports")
    page_views = [w for w in backend.writes if w["event"] == "page_view"]
    assert len(page_views) == 2
    assert json.loads(page_views[1]["properties"])["page"] == "Reports"


def test_page_return_to_prior_page_emits_fresh_view(tracker):
    """Home -> Reports -> Home yields three page_views (return counts as a visit)."""
    t, backend, session_state = tracker
    with patch("streamlit_fyr.tracker.st.session_state", session_state):
        t.page("Home")
        t.page("Reports")
        t.page("Home")
    pages = [
        json.loads(w["properties"])["page"]
        for w in backend.writes
        if w["event"] == "page_view"
    ]
    assert pages == ["Home", "Reports", "Home"]
