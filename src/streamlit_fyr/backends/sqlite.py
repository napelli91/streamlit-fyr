import os

from sqlalchemy import create_engine
from sqlalchemy import event as sa_event

from .models import SQLAlchemyBackend

_DEFAULT_DB_PATH = "telemetry.db"


class SQLiteBackend(SQLAlchemyBackend):
    def __init__(self, db_path: str | None = None) -> None:
        db_path = db_path or os.environ.get("ST_FYR_SQLITE_FILE", _DEFAULT_DB_PATH)
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )

        @sa_event.listens_for(engine, "connect")
        def set_wal(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA journal_mode=WAL")

        super().__init__(engine)
