"""Tests for 0.3.0 schema-setup changes (#9 schema gating, #10 indexes, #3 query
params) and the version bump."""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy import inspect as sa_inspect

from streamlit_fyr.backends.models import SQLAlchemyBackend
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

EXPECTED_INDEXES = {
    "ix_events_app_name_timestamp",
    "ix_events_user_id",
    "ix_events_visitor_id",
}


# --- #9: schema-setup gating --------------------------------------------------


def test_default_ensure_schema_creates_and_roundtrips(tmp_path):
    """SQLiteBackend() defaults to ensure_schema=True: table exists, write+query."""
    backend = SQLiteBackend(str(tmp_path / "default.db"))
    assert sa_inspect(backend._engine).has_table("events")
    backend.write(SAMPLE_EVENT)
    df = backend.query("SELECT * FROM events")
    assert len(df) == 1
    assert df.iloc[0]["event"] == "page_view"


def test_ensure_schema_false_does_no_ddl(tmp_path):
    """ensure_schema=False against a fresh DB must NOT create the events table."""
    db_path = str(tmp_path / "nodll.db")
    backend = SQLiteBackend(db_path, ensure_schema=False)
    assert not sa_inspect(backend._engine).has_table("events")


def test_ensure_schema_false_then_manual_ensure_creates_table(tmp_path):
    """Calling ensure_schema() after ensure_schema=False provisions the table."""
    db_path = str(tmp_path / "manual.db")
    backend = SQLiteBackend(db_path, ensure_schema=False)
    assert not sa_inspect(backend._engine).has_table("events")

    backend.ensure_schema()
    assert sa_inspect(backend._engine).has_table("events")

    # Round-trips once provisioned.
    backend.write(SAMPLE_EVENT)
    assert len(backend.query("SELECT * FROM events")) == 1


def test_ensure_schema_is_idempotent(tmp_path):
    """A second ensure_schema() call is a no-op and does not raise."""
    backend = SQLiteBackend(str(tmp_path / "idem.db"), ensure_schema=False)
    backend.ensure_schema()
    backend.ensure_schema()  # must not raise
    assert sa_inspect(backend._engine).has_table("events")
    indexes = {ix["name"] for ix in sa_inspect(backend._engine).get_indexes("events")}
    assert EXPECTED_INDEXES.issubset(indexes)


def test_sqlite_default_triggers_ensure_schema(tmp_path):
    """SQLiteBackend default must invoke ensure_schema() during construction."""
    with patch.object(SQLAlchemyBackend, "ensure_schema") as spy:
        SQLiteBackend(str(tmp_path / "spy.db"))
    spy.assert_called_once()


def test_sqlite_ensure_schema_false_skips_setup(tmp_path):
    """ensure_schema=False must NOT invoke ensure_schema() during construction."""
    with patch.object(SQLAlchemyBackend, "ensure_schema") as spy:
        SQLiteBackend(str(tmp_path / "spy2.db"), ensure_schema=False)
    spy.assert_not_called()


def test_postgres_default_skips_ensure_schema(monkeypatch):
    """PostgresBackend default (ensure_schema=False) must NOT run schema setup."""
    from streamlit_fyr.backends import postgres as pg_mod

    monkeypatch.delenv("ST_FYR_CONNECTION_STRING", raising=False)
    with patch.object(pg_mod, "create_engine", return_value=MagicMock()):
        with patch.object(SQLAlchemyBackend, "ensure_schema") as spy:
            pg_mod.PostgresBackend("postgresql://host/db")
    spy.assert_not_called()


def test_postgres_ensure_schema_true_runs_setup(monkeypatch):
    """PostgresBackend(ensure_schema=True) must run schema setup at construction."""
    from streamlit_fyr.backends import postgres as pg_mod

    monkeypatch.delenv("ST_FYR_CONNECTION_STRING", raising=False)
    with patch.object(pg_mod, "create_engine", return_value=MagicMock()):
        with patch.object(SQLAlchemyBackend, "ensure_schema") as spy:
            pg_mod.PostgresBackend("postgresql://host/db", ensure_schema=True)
    spy.assert_called_once()


# --- #10: indexes -------------------------------------------------------------


def test_ensure_schema_creates_all_indexes(tmp_path):
    """After ensure_schema() all three named indexes exist on events."""
    backend = SQLiteBackend(str(tmp_path / "idx.db"))
    indexes = {ix["name"] for ix in sa_inspect(backend._engine).get_indexes("events")}
    assert EXPECTED_INDEXES.issubset(indexes)


def test_composite_index_columns(tmp_path):
    """The composite index covers (app_name, timestamp) in order."""
    backend = SQLiteBackend(str(tmp_path / "composite.db"))
    by_name = {
        ix["name"]: ix for ix in sa_inspect(backend._engine).get_indexes("events")
    }
    assert by_name["ix_events_app_name_timestamp"]["column_names"] == [
        "app_name",
        "timestamp",
    ]


def test_ensure_indexes_on_preexisting_table(tmp_path):
    """A table that predates the indexes gets them added by ensure_schema().

    create_all() only adds indexes to a table it creates, so this exercises the
    _ensure_indexes() explicit-create path against an already-existing table.
    """
    db_path = str(tmp_path / "preexisting.db")
    # Raw table without any of the named indexes.
    with sqlite3.connect(db_path) as con:
        con.execute("""
            CREATE TABLE events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT NOT NULL,
                session_id TEXT,
                visitor_id TEXT,
                user_id    TEXT,
                app_name   TEXT NOT NULL,
                page       TEXT,
                event      TEXT NOT NULL,
                properties TEXT
            )
            """)

    backend = SQLiteBackend(db_path, ensure_schema=False)
    before = {ix["name"] for ix in sa_inspect(backend._engine).get_indexes("events")}
    assert not EXPECTED_INDEXES & before

    backend.ensure_schema()
    after = {ix["name"] for ix in sa_inspect(backend._engine).get_indexes("events")}
    assert EXPECTED_INDEXES.issubset(after)


def test_ensure_indexes_idempotent(tmp_path):
    """Calling ensure_schema() twice keeps exactly the three expected indexes."""
    backend = SQLiteBackend(str(tmp_path / "idx_idem.db"))
    backend.ensure_schema()
    indexes = {ix["name"] for ix in sa_inspect(backend._engine).get_indexes("events")}
    assert EXPECTED_INDEXES.issubset(indexes)


# --- #3: query named params ---------------------------------------------------


def test_query_with_named_params_matches(tmp_path):
    backend = SQLiteBackend(str(tmp_path / "params.db"))
    backend.write({**SAMPLE_EVENT, "app_name": "demo"})
    backend.write({**SAMPLE_EVENT, "app_name": "other"})

    df = backend.query("SELECT * FROM events WHERE app_name = :app", {"app": "demo"})
    assert len(df) == 1
    assert df.iloc[0]["app_name"] == "demo"


def test_query_with_named_params_no_match(tmp_path):
    backend = SQLiteBackend(str(tmp_path / "params2.db"))
    backend.write({**SAMPLE_EVENT, "app_name": "demo"})

    df = backend.query("SELECT * FROM events WHERE app_name = :app", {"app": "nope"})
    assert len(df) == 0


def test_query_without_params(tmp_path):
    backend = SQLiteBackend(str(tmp_path / "noparams.db"))
    backend.write(SAMPLE_EVENT)
    df = backend.query("SELECT * FROM events")
    assert len(df) == 1


def test_query_positional_tuple_params_not_supported(tmp_path):
    """The old tuple contract never worked with text() SQL; keep it unsupported."""
    backend = SQLiteBackend(str(tmp_path / "tupleparams.db"))
    backend.write({**SAMPLE_EVENT, "app_name": "demo"})
    with pytest.raises(Exception):
        backend.query("SELECT * FROM events WHERE app_name = :app", ("demo",))


# --- #5 P0 regression: implicit_returning stays off after the tuple refactor ---


def test_insert_emits_no_returning_for_postgres_dialect():
    """__table_args__ became a tuple in 0.3.0; ensure it still disables RETURNING."""
    from sqlalchemy import insert
    from sqlalchemy.dialects import postgresql

    from streamlit_fyr.backends.models import Event

    compiled = insert(Event).compile(
        dialect=postgresql.dialect(), column_keys=list(SAMPLE_EVENT)
    )
    assert "RETURNING" not in str(compiled).upper()
    assert Event.__table__.implicit_returning is False


# --- version ------------------------------------------------------------------


def test_version_is_0_3_1():
    import streamlit_fyr

    assert streamlit_fyr.__version__ == "0.3.1"
