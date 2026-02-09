"""Canonical EW core models.

This file is intentionally *stable* and backward-compatible.
Some earlier scaffolds had different names; we provide aliases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class WaveLeg:
    """A single leg between two points (index + price)."""
    start_idx: int
    end_idx: int
    start_px: float
    end_px: float

    @property
    def direction(self) -> int:
        if self.end_px > self.start_px:
            return 1
        if self.end_px < self.start_px:
            return -1
        return 0

    @property
    def abs_move(self) -> float:
        return abs(self.end_px - self.start_px)


@dataclass
class WavePattern:
    """A detected wave pattern (e.g., impulse 1-5)."""
    kind: str
    legs: List[WaveLeg]
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def start_idx(self) -> int:
        return self.legs[0].start_idx if self.legs else 0

    @property
    def end_idx(self) -> int:
        return self.legs[-1].end_idx if self.legs else 0

    @property
    def start_px(self) -> float:
        return self.legs[0].start_px if self.legs else 0.0

    @property
    def end_px(self) -> float:
        return self.legs[-1].end_px if self.legs else 0.0


# Backward-compat aliases (older code might import these names)
Leg = WaveLeg
Pattern = WavePattern
