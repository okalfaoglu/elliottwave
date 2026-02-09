from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MarketType(str, Enum):
    spot = "spot"
    futures = "futures"


@dataclass(frozen=True)
class Instrument:
    """A normalized instrument identifier."""
    symbol: str
    venue: str
    market: MarketType = MarketType.spot


@dataclass(frozen=True)
class TimeRange:
    start_ms: Optional[int] = None  # Unix epoch milliseconds (inclusive)
    end_ms: Optional[int] = None    # Unix epoch milliseconds (exclusive)
