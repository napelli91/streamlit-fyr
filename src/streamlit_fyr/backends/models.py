from typing import Any

import pandas as pd
from sqlalchemy import Column, Index, Integer, Text, insert
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

from .base import Backend


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"
    # Indexes back the dashboard/query workload, which filters by app_name,
    # timestamp, user_id, and visitor_id. Note: create_all() only adds these to
    # a table it is creating — missing indexes on a pre-existing table are added
    # by SQLAlchemyBackend.ensure_schema().
    #
    # implicit_returning=False stops SQLAlchemy from appending a RETURNING
    # events.id clause to INSERTs on dialects that support it (e.g. Postgres).
    # By default an autoincrement PK triggers implicit RETURNING to populate
    # inserted_primary_key, which requires SELECT on the table and fails for
    # INSERT-only roles. We never read the generated id back, so we disable it.
    # (Using a Core insert() in write() is not sufficient on its own: the
    # RETURNING clause is added regardless of the write path.)
    __table_args__ = (
        Index("ix_events_app_name_timestamp", "app_name", "timestamp"),
        Index("ix_events_user_id", "user_id"),
        Index("ix_events_visitor_id", "visitor_id"),
        {"implicit_returning": False},
    )

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
    def __init__(self, engine: Engine, ensure_schema: bool) -> None:
        """Base for SQLAlchemy-backed event stores.

        Args:
            engine: A configured SQLAlchemy ``Engine``.
            ensure_schema: When True, run schema setup (``ensure_schema()``)
                during construction. When False, no DDL/catalog work is done —
                the caller is responsible for having provisioned the schema
                (see ``ensure_schema``). Subclasses choose the default.
        """
        self._engine = engine
        if ensure_schema:
            self.ensure_schema()

    def ensure_schema(self) -> None:
        """Provision/upgrade the events schema. Idempotent.

        Creates the ``events`` table if missing, backfills the ``user_id``
        column on tables created before it existed, and creates any missing
        indexes (``create_all`` does not add indexes to a table that already
        exists). Run this once at deploy time with a privileged role; runtime
        apps can then construct backends with ``ensure_schema=False`` (and use
        INSERT-only roles) and skip all DDL.
        """
        Base.metadata.create_all(self._engine)
        self._migrate()
        self._ensure_indexes()

    def _migrate(self) -> None:
        inspector = sa_inspect(self._engine)
        columns = [c["name"] for c in inspector.get_columns("events")]
        if "user_id" not in columns:
            with self._engine.connect() as con:
                con.execute(text("ALTER TABLE events ADD COLUMN user_id TEXT"))
                con.commit()

    def _ensure_indexes(self) -> None:
        # create_all() adds indexes only when it creates the table, so a table
        # that predates the indexes needs them added explicitly. checkfirst
        # makes each create a no-op when the index already exists.
        for index in Base.metadata.tables["events"].indexes:
            index.create(bind=self._engine, checkfirst=True)

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
