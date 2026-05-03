import pandas as pd
import pytest

from streamlit_fyr.backends.base import Backend


class FakeSessionState(dict):
    """Mimics st.session_state — supports both attribute and item access."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value


class MockBackend(Backend):
    """In-memory backend that captures write() calls for assertions."""

    def __init__(self):
        self.writes: list[dict] = []

    def write(self, event: dict) -> None:
        self.writes.append(event)

    def query(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        return pd.DataFrame()


@pytest.fixture
def session_state():
    state = FakeSessionState()
    state["session_id"] = "test-session-id"
    state["visitor_id"] = "test-visitor-id"
    return state


@pytest.fixture
def mock_backend():
    return MockBackend()
