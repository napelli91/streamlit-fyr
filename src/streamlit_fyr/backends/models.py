import pandas as pd
from sqlalchemy import Column, Integer, Text, create_engine, event as sa_event, text
from sqlalchemy.orm import DeclarativeBase, Session

from .base import Backend


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    timestamp  = Column(Text, nullable=False)
    session_id = Column(Text, nullable=False)
    visitor_id = Column(Text)
    app_name   = Column(Text, nullable=False)
    page       = Column(Text)
    event      = Column(Text, nullable=False)
    properties = Column(Text)


class SQLAlchemyBackend(Backend):
    def __init__(self, engine) -> None:
        self._engine = engine
        Base.metadata.create_all(self._engine)

    def write(self, event: dict) -> None:
        with Session(self._engine) as session:
            session.add(Event(**event))
            session.commit()

    def query(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        with self._engine.connect() as con:
            return pd.read_sql_query(text(sql), con, params=params)
