from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class Backend(ABC):
    @abstractmethod
    def write(self, event: dict[str, Any]) -> None:
        """Persist a single event record."""
        ...

    @abstractmethod
    def query(self, sql: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
        """Execute a SELECT and return results as a DataFrame."""
        ...
