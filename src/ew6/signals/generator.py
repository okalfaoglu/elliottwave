from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from ew6.ew.core.model import WavePattern


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"
    FLAT = "flat"


@dataclass(frozen=True)
class Signal:
    side: Side
    confidence: float
    reason: str
    pattern: Optional[WavePattern] = None


@dataclass(frozen=True)
class SignalConfig:
    min_score: float = 0.0


def generate_signals(patterns: List[WavePattern], cfg: SignalConfig) -> List[Signal]:
    """Convert wave patterns to trade signals.

    Placeholder policy: take top pattern and emit BUY if it starts with a LOW,
    SELL if it starts with a HIGH.
    """
    if not patterns:
        return [Signal(side=Side.FLAT, confidence=0.0, reason="no_patterns")]

    best = max(patterns, key=lambda p: p.score)
    if best.score < cfg.min_score:
        return [Signal(side=Side.FLAT, confidence=0.0, reason="low_score", pattern=best)]

    # naive: compare first/last price
    if best.points[-1].price > best.points[0].price:
        return [Signal(side=Side.BUY, confidence=min(1.0, max(0.1, best.score)), reason="impulse_up", pattern=best)]
    return [Signal(side=Side.SELL, confidence=min(1.0, max(0.1, best.score)), reason="impulse_down", pattern=best)]
