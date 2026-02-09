from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class Bar:
    """Single OHLCV bar."""

    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None


@dataclass(frozen=True)
class BarSeries:
    """A thin wrapper around a pandas DataFrame with columns: open,high,low,close,volume.

    Index must be datetime-like.
    """

    df: pd.DataFrame

    def validate(self) -> None:
        req = {"open", "high", "low", "close"}
        missing = req - set(self.df.columns)
        if missing:
            raise ValueError(f"BarSeries missing columns: {sorted(missing)}")
        if not isinstance(self.df.index, pd.DatetimeIndex):
            raise TypeError("BarSeries index must be a pandas.DatetimeIndex")

    @property
    def close(self) -> pd.Series:
        return self.df["close"]
