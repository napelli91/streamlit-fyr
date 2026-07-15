from typing import Any

import pandas as pd
from sqlalchemy import Column, Integer, Text, insert
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

from .base import Backend


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"
    # implicit_returning=False stops SQLAlchemy from appending a RETURNING
    # events.id clause to INSERTs on dialects that support it (e.g. Postgres).
    # By default an autoincrement PK triggers implicit RETURNING to populate
    # inserted_primary_key, which requires SELECT on the table and fails for
    # INSERT-only roles. We never read the generated id back, so we disable it.
    # (Using a Core insert() in write() is not sufficient on its own: the
    # RETURNING clause is added regardless of the write path.)
    __table_args__ = {"implicit_returning": False}

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(Text, nullable=False)
    session_id = Column(Text)
    visitor_id = Column(Text)
    user_id = Column(Text)
    app_name = Column(Text, nullable=False)
    page = Column(Text)
    event = Column(Text, nullable=False)
    properties = Column(Text)


class SQLAlchemyBackend(Backend):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        Base.metadata.create_all(self._engine)
        self._migrate()

    def _migrate(self) -> None:
        inspector = sa_inspect(self._engine)
        columns = [c["name"] for c in inspector.get_columns("events")]
        if "user_id" not in columns:
            with self._engine.connect() as con:
                con.execute(text("ALTER TABLE events ADD COLUMN user_id TEXT"))
                con.commit()

    def write(self, event: dict[str, Any]) -> None:
        # Use a Core INSERT rather than an ORM insert (session.add) to avoid
        # the ORM's PK-fetch machinery. The RETURNING clause itself is
        # suppressed by implicit_returning=False on the Event table (see the
        # note there) — that is what makes this safe for INSERT-only roles.
        with self._engine.connect() as con:
            con.execute(insert(Event), event)
            con.commit()

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
        with self._engine.connect() as con:
            return pd.read_sql_query(text(sql), con, params=params)
