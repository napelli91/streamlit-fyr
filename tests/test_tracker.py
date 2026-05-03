import json
from unittest.mock import patch

import pytest

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
