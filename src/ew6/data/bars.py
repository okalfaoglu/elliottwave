"""Minimal OHLCV bar models (stable surface).

Some parts of the project (connectors/zigzag/CLI/export) expect a BarSeries with:
- bars: list[Bar]
- df: pandas DataFrame (DatetimeIndex UTC)
- start_time / end_time properties
- from_bars constructor

We keep this module intentionally tiny and dependency-light.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Optional

import pandas as pd


@dataclass(frozen=True)
class Bar:
    ts: int  # milliseconds since epoch (UTC)
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class BarSeries:
    def __init__(self, bars: List[Bar]):
        self.bars: List[Bar] = bars
        self._df: Optional[pd.DataFrame] = None

    @staticmethod
    def from_bars(bars: List[Bar]) -> "BarSeries":
        return BarSeries(bars)

    def __len__(self) -> int:
        return len(self.bars)

    def __iter__(self) -> Iterator[Bar]:
        return iter(self.bars)

    @property
    def df(self) -> pd.DataFrame:
        if self._df is None:
            idx = pd.to_datetime([int(b.ts) for b in self.bars], unit="ms", utc=True)
            self._df = pd.DataFrame(
                {
                    "ts": [int(b.ts) for b in self.bars],
                    "open": [float(b.open) for b in self.bars],
                    "high": [float(b.high) for b in self.bars],
                    "low": [float(b.low) for b in self.bars],
                    "close": [float(b.close) for b in self.bars],
                    "volume": [float(b.volume) for b in self.bars],
                },
                index=idx,
            )
        return self._df

    def to_df(self) -> pd.DataFrame:
        return self.df.copy()

    @property
    def start_time(self):
        if not self.bars:
            return None
        return pd.to_datetime(int(self.bars[0].ts), unit="ms", utc=True)

    @property
    def end_time(self):
        if not self.bars:
            return None
        return pd.to_datetime(int(self.bars[-1].ts), unit="ms", utc=True)
