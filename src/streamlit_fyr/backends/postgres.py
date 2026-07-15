import os
from typing import Any

from sqlalchemy import create_engine

from .models import SQLAlchemyBackend


class PostgresBackend(SQLAlchemyBackend):
    def __init__(
        self,
        connection_string: str | None = None,
        pool_size: int = 5,
        max_overflow: int = 5,
        pool_pre_ping: bool = True,
        ensure_schema: bool = False,
        **engine_kwargs: Any,
    ) -> None:
        """Postgres-backed event store.

        Args:
            connection_string: SQLAlchemy URL. Falls back to the
                ``ST_FYR_CONNECTION_STRING`` env var; raises ``ValueError`` if
                neither is set.
            pool_size: Base number of pooled connections (SQLAlchemy default is
                5; we set it explicitly to keep the footprint modest).
            max_overflow: Extra connections allowed beyond ``pool_size``.
            pool_pre_ping: Test connections for liveness before use, so stale
                connections (e.g. after a DB restart) are transparently
                recycled instead of failing a write.
            ensure_schema: Default False for production safety. Runtime apps
                should use an INSERT-only role and do no DDL; provision the
                schema once at deploy time with a privileged role by calling
                ``ensure_schema()``. Set True only if the app's role is allowed
                to run DDL and you want the table created on construction.
            **engine_kwargs: Extra keyword arguments forwarded to
                ``create_engine`` (e.g. ``pool_recycle``, ``echo``).

        Note:
            ``create_engine`` builds a connection pool. Streamlit re-runs the
            whole script on every interaction, so constructing this backend at
            module scope leaks a new pool per rerun and can exhaust Postgres
            ``max_connections``. Cache the backend with ``@st.cache_resource``
            (see the README) so a single pool is reused across reruns.
        """
        connection_string = connection_string or os.environ.get(
            "ST_FYR_CONNECTION_STRING"
        )
        if not connection_string:
            raise ValueError(
                "PostgresBackend requires a connection_string argument or "
                "ST_FYR_CONNECTION_STRING env var."
            )
        engine = create_engine(
            connection_string,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=pool_pre_ping,
            **engine_kwargs,
        )
        super().__init__(engine, ensure_schema=ensure_schema)
