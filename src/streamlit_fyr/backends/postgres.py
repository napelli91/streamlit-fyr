import os

from sqlalchemy import create_engine

from .models import SQLAlchemyBackend


class PostgresBackend(SQLAlchemyBackend):
    def __init__(self, connection_string: str | None = None) -> None:
        connection_string = connection_string or os.environ.get(
            "ST_FYR_CONNECTION_STRING"
        )
        if not connection_string:
            raise ValueError(
                "PostgresBackend requires a connection_string argument or "
                "ST_FYR_CONNECTION_STRING env var."
            )
        engine = create_engine(connection_string)
        super().__init__(engine)
