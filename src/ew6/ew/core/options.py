"""WaveOptions / tuning knobs (M1).

We keep options small and explicit so we can grid-search reasonable defaults.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WaveOptions:
    monowave_skip: int = 1
    min_leg_abs_move: float = 0.0

    max_gap: int = 1
    beam_width: int = 256
    max_candidates: int = 5000

    max_patterns: int = 50
    nms_overlap: float = 0.70
