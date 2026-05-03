from sqlalchemy import create_engine

from .models import SQLAlchemyBackend


class PostgresBackend(SQLAlchemyBackend):
    def __init__(self, connection_string: str) -> None:
        engine = create_engine(connection_string)
        super().__init__(engine)
