from abc import ABC, abstractmethod

import pandas as pd


class Backend(ABC):
    @abstractmethod
    def write(self, event: dict) -> None:
        """Persist a single event record."""
        ...

    @abstractmethod
    def query(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        """Execute a SELECT and return results as a DataFrame."""
        ...
