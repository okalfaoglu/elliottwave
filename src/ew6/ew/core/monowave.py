"""MonoWave utilities (P5-inspired).

This module is intentionally backward-compatible:
- provides MonoWaveConfig
- provides build_monowaves_from_swings(swings, cfg)

`swings` is expected to be a sequence of swing points produced by ew6.swing.zigzag.
We support common representations:
- dict with keys: idx/index, price/px/value
- object with attributes: idx/index and price/px/value
- tuple: (idx, price) or (idx, price, ...)

M1 note: The skip logic here is conservative (down-sampling swings). We will refine it in the next iteration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Sequence, Tuple, Optional


@dataclass(frozen=True)
class MonoWaveConfig:
    skip: int = 1
    min_abs_move: float = 0.0


@dataclass(frozen=True)
class MonoWave:
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


def _get_idx_px(sp: Any) -> Tuple[int, float]:
    # dict
    if isinstance(sp, dict):
        idx = sp.get("idx", sp.get("index"))
        px = sp.get("price", sp.get("px", sp.get("value")))
        if idx is None or px is None:
            raise ValueError(f"Swing dict missing idx/price keys: {sp.keys()}")
        return int(idx), float(px)
    # tuple/list
    if isinstance(sp, (tuple, list)) and len(sp) >= 2:
        return int(sp[0]), float(sp[1])
    # object attrs
    for ik in ("idx", "index"):
        if hasattr(sp, ik):
            idx = getattr(sp, ik)
            break
    else:
        idx = None
    for pk in ("price", "px", "value"):
        if hasattr(sp, pk):
            px = getattr(sp, pk)
            break
    else:
        px = None
    if idx is None or px is None:
        raise ValueError(f"Unsupported swing point type: {type(sp)}")
    return int(idx), float(px)


def build_monowaves_from_swings(swings: Sequence[Any], cfg: MonoWaveConfig) -> List[MonoWave]:
    """Convert swing points to monowaves."""
    if not swings or len(swings) < 2:
        return []

    # normalize to (idx, px) and ensure sorted by idx
    pts = [_get_idx_px(s) for s in swings]
    pts.sort(key=lambda x: x[0])

    # simple skip = downsample swings to reduce noise
    step = max(1, int(cfg.skip) + 1)
    filtered = pts[::step]
    if filtered[-1] != pts[-1]:
        filtered.append(pts[-1])

    mws: List[MonoWave] = []
    for (i0, p0), (i1, p1) in zip(filtered[:-1], filtered[1:]):
        mw = MonoWave(start_idx=i0, end_idx=i1, start_px=p0, end_px=p1)
        if cfg.min_abs_move > 0 and mw.abs_move < cfg.min_abs_move:
            continue
        mws.append(mw)

    return mws


# Backward compat alias (some code may import this)
build_monowaves = build_monowaves_from_swings
