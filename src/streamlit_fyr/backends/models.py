from typing import Any

import pandas as pd
from sqlalchemy import Column, Integer, Text
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session

from .base import Backend


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

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
        with Session(self._engine) as session:
            session.add(Event(**event))
            session.commit()

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
        with self._engine.connect() as con:
            return pd.read_sql_query(text(sql), con, params=params)
