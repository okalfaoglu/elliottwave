"""Scoring and confidence calibration for Elliott patterns.

M1 version:
- reward close-to-Fibonacci ratios for wave2/wave3/wave4
- penalize overlap and extreme leg imbalance
- confidence in [0,1] from score (sigmoid)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple
import math

from ew6.ew.core.model import WavePattern


@dataclass(frozen=True)
class ScoreConfig:
    fib_w2: Tuple[float, float] = (0.236, 0.786)
    fib_w3: Tuple[float, float] = (1.0, 2.618)  # relative to wave1
    fib_w4: Tuple[float, float] = (0.236, 0.786)
    overlap_penalty: float = 2.5
    extreme_penalty: float = 1.0


def _within(x: float, lo: float, hi: float) -> float:
    if lo <= x <= hi:
        return 1.0
    if x < lo:
        return math.exp(-((lo - x) / lo) * 2.0) if lo > 0 else 0.0
    return math.exp(-((x - hi) / hi) * 2.0) if hi > 0 else 0.0


def score_impulse(pattern: WavePattern, cfg: ScoreConfig = ScoreConfig()) -> float:
    legs = pattern.legs
    if len(legs) != 5:
        return 0.0

    m = [abs(l.end_px - l.start_px) for l in legs]
    if min(m) <= 0:
        return 0.0

    w1, w2, w3, w4, w5 = m
    r2 = w2 / w1
    r3 = w3 / w1
    r4 = w4 / w3 if w3 > 0 else 0.0

    s = 0.0
    s += 2.0 * _within(r2, *cfg.fib_w2)
    s += 2.0 * _within(r3, *cfg.fib_w3)
    s += 1.5 * _within(r4, *cfg.fib_w4)

    if w3 > min(w1, w5):
        s += 1.0

    if pattern.meta.get("w4_overlap", False):
        s -= cfg.overlap_penalty

    mx = max(m)
    mn = min(m)
    if mn > 0 and mx / mn > 10:
        s -= cfg.extreme_penalty

    span = pattern.end_idx - pattern.start_idx
    s += min(max(span / 500.0, 0.0), 0.5)
    return float(s)


def confidence_from_score(score: float) -> float:
    return float(1.0 / (1.0 + math.exp(-(score - 2.5))))
