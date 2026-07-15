from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

import pandas as pd


class Backend(ABC):
    @abstractmethod
    def write(self, event: dict[str, Any]) -> None:
        """Persist a single event record."""
        ...

    @abstractmethod
    def query(self, sql: str, params: Mapping[str, Any] | None = None) -> pd.DataFrame:
        """Execute a SELECT and return results as a DataFrame.

        Args:
            sql: A SELECT statement. Bind parameters use named placeholders
                (e.g. ``:app_name``).
            params: Optional mapping of parameter name to value. Positional
                tuples are not supported — pandas binds named parameters from a
                mapping.
        """
        ...
