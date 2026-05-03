from sqlalchemy import create_engine, event as sa_event

from .models import SQLAlchemyBackend


class SQLiteBackend(SQLAlchemyBackend):
    def __init__(self, db_path: str = "telemetry.db") -> None:
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )

        @sa_event.listens_for(engine, "connect")
        def set_wal(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA journal_mode=WAL")

        super().__init__(engine)
