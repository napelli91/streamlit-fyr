import os
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy import event as sa_event

from .models import SQLAlchemyBackend

_DEFAULT_DB_PATH = "telemetry.db"


class SQLiteBackend(SQLAlchemyBackend):
    def __init__(self, db_path: str | None = None, ensure_schema: bool = True) -> None:
        """SQLite-backed event store.

        Args:
            db_path: Path to the SQLite file. Falls back to the
                ``ST_FYR_SQLITE_FILE`` env var, then ``telemetry.db``.
            ensure_schema: Default True for the zero-config local/dev story —
                the table (and indexes) are created on construction. Set False
                to skip all DDL and provision the schema yourself via
                ``ensure_schema()``.
        """
        db_path = db_path or os.environ.get("ST_FYR_SQLITE_FILE", _DEFAULT_DB_PATH)
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )

        @sa_event.listens_for(engine, "connect")
        def set_wal(dbapi_conn: Any, _: Any) -> None:
            dbapi_conn.execute("PRAGMA journal_mode=WAL")

        super().__init__(engine, ensure_schema=ensure_schema)
