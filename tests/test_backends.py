import sqlite3
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from streamlit_fyr.backends.sqlite import SQLiteBackend

SAMPLE_EVENT = {
    "timestamp": "2026-05-03T10:00:00+00:00",
    "session_id": "sess-abc",
    "visitor_id": "vis-xyz",
    "user_id": None,
    "app_name": "test_app",
    "page": "home",
    "event": "page_view",
    "properties": "{}",
}


@pytest.fixture
def backend(tmp_path):
    return SQLiteBackend(str(tmp_path / "test.db"))


def test_write_and_query_roundtrip(backend):
    backend.write(SAMPLE_EVENT)
    df = backend.query("SELECT * FROM events")
    assert len(df) == 1
    row = df.iloc[0]
    assert row["event"] == "page_view"
    assert row["app_name"] == "test_app"
    assert row["session_id"] == "sess-abc"
    assert row["visitor_id"] == "vis-xyz"


def test_schema_has_all_columns(backend):
    df = backend.query("SELECT * FROM events LIMIT 0")
    expected = {
        "id",
        "timestamp",
        "session_id",
        "visitor_id",
        "user_id",
        "app_name",
        "page",
        "event",
        "properties",
    }
    assert expected.issubset(set(df.columns))


def test_user_id_stored_and_retrieved(backend):
    backend.write({**SAMPLE_EVENT, "user_id": "user-42"})
    df = backend.query("SELECT user_id FROM events")
    assert df.iloc[0]["user_id"] == "user-42"


def test_user_id_nullable(backend):
    backend.write({**SAMPLE_EVENT, "user_id": None})
    df = backend.query("SELECT user_id FROM events")
    assert df.iloc[0]["user_id"] is None or pd.isna(df.iloc[0]["user_id"])


def test_multiple_writes(backend):
    for i in range(5):
        backend.write({**SAMPLE_EVENT, "session_id": f"sess-{i}"})
    df = backend.query("SELECT * FROM events")
    assert len(df) == 5


def test_query_filters_by_app(backend):
    backend.write({**SAMPLE_EVENT, "app_name": "app_a"})
    backend.write({**SAMPLE_EVENT, "app_name": "app_b"})
    df = backend.query("SELECT * FROM events WHERE app_name = 'app_a'")
    assert len(df) == 1
    assert df.iloc[0]["app_name"] == "app_a"


def test_migrate_adds_user_id_to_existing_db(tmp_path):
    """Backend must add user_id column to DBs created before that column existed."""
    db_path = str(tmp_path / "legacy.db")
    with sqlite3.connect(db_path) as con:
        con.execute("""
            CREATE TABLE events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT NOT NULL,
                session_id TEXT NOT NULL,
                visitor_id TEXT,
                app_name   TEXT NOT NULL,
                page       TEXT,
                event      TEXT NOT NULL,
                properties TEXT
            )
        """)

    backend = SQLiteBackend(db_path)
    df = backend.query("SELECT * FROM events LIMIT 0")
    assert "user_id" in df.columns


def test_wal_mode_enabled(tmp_path):
    db_path = str(tmp_path / "wal.db")
    SQLiteBackend(db_path)
    with sqlite3.connect(db_path) as con:
        mode = con.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"


def test_sqlite_env_var_fallback(tmp_path, monkeypatch):
    db_path = tmp_path / "from_env.db"
    monkeypatch.setenv("ST_FYR_SQLITE_FILE", str(db_path))
    SQLiteBackend()
    assert db_path.exists()


def test_postgres_requires_connection_string(monkeypatch):
    from streamlit_fyr.backends.postgres import PostgresBackend

    monkeypatch.delenv("ST_FYR_CONNECTION_STRING", raising=False)
    with pytest.raises(ValueError, match="ST_FYR_CONNECTION_STRING"):
        PostgresBackend()


def test_postgres_env_var_fallback(monkeypatch):
    from streamlit_fyr.backends import postgres as pg_mod

    monkeypatch.setenv("ST_FYR_CONNECTION_STRING", "postgresql://from-env/db")
    with patch.object(pg_mod, "create_engine", return_value=MagicMock()) as mk:
        with patch.object(pg_mod.SQLAlchemyBackend, "__init__", return_value=None):
            pg_mod.PostgresBackend()
    mk.assert_called_once_with("postgresql://from-env/db")
