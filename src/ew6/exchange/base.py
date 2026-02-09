from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from ew6.data.types import BarSeries
from ew6.exchange.types import Instrument


@dataclass(frozen=True)
class OHLCVRequest:
    instrument: Instrument
    timeframe: str = "5m"
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None
    limit: int = 1000


@dataclass(frozen=True)
class TradesRequest:
    instrument: Instrument
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None
    limit: int = 1000
    paginate: bool = True
    max_records: int = 200_000
    progress: bool = False


class MarketDataConnector(ABC):
    """Minimal interface for market data connectors (REST-first)."""

    @abstractmethod
    def fetch_ohlcv(self, req: OHLCVRequest) -> BarSeries:
        raise NotImplementedError

    @abstractmethod
    def fetch_trades(self, req: TradesRequest) -> pd.DataFrame:
        """Return trades indexed by UTC timestamp with at least: price, size (optional)."""
        raise NotImplementedError
