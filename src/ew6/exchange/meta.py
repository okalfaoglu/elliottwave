"""Fetch metadata helpers (M1).

We keep this separate so connectors can expose useful runtime info (caps, paging, etc.)
without changing return types (backward compatible).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class FetchMeta:
    venue: str
    market: str
    kind: str  # ohlcv/trades
    requested_start_ms: Optional[int] = None
    requested_end_ms: Optional[int] = None
    earliest_ms: Optional[int] = None
    latest_ms: Optional[int] = None
    records: int = 0
    pages: int = 0
    cap_reason: str = ""   # "", "max_records", "start_reached", "empty", "error"
    notes: str = ""        # free-form debug hint
