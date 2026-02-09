"""Rule checks for impulse patterns (P5-inspired).

This file provides a stable API:
- is_valid_impulse_from_monowaves(mws, return_meta=False) -> bool or (bool, meta)

`mws` is a sequence of 5 MonoWave-like objects with:
- start_idx, end_idx, start_px, end_px and direction property (or derivable)

Rules implemented (conservative M1):
- directions alternate: 1, -1, 1, -1, 1 (or opposite for downward)
- wave2 does not retrace beyond wave1 start (in price)
- wave3 is not the shortest among (1,3,5)
- basic wave4 overlap heuristic flag (stored in meta) - not hard fail by default
"""

from __future__ import annotations

from typing import Any, Dict, Sequence, Tuple


def _dir(mw: Any) -> int:
    if hasattr(mw, "direction"):
        return int(mw.direction)
    # derive from prices
    if mw.end_px > mw.start_px:
        return 1
    if mw.end_px < mw.start_px:
        return -1
    return 0


def _abs_move(mw: Any) -> float:
    if hasattr(mw, "abs_move"):
        return float(mw.abs_move)
    return float(abs(mw.end_px - mw.start_px))


def is_valid_impulse_from_monowaves(mws: Sequence[Any], return_meta: bool = False):
    if len(mws) != 5:
        return (False, {}) if return_meta else False

    d = [_dir(x) for x in mws]
    if 0 in d:
        return (False, {}) if return_meta else False

    # Determine expected sign based on first leg
    s = d[0]
    expected = [s, -s, s, -s, s]
    if d != expected:
        return (False, {}) if return_meta else False

    # Price points
    p0 = mws[0].start_px
    p1 = mws[0].end_px
    p2 = mws[1].end_px
    p3 = mws[2].end_px
    p4 = mws[3].end_px
    p5 = mws[4].end_px

    meta: Dict[str, bool] = {}

    # wave2 retrace beyond start invalid
    if s == 1:
        if p2 <= p0:
            return (False, {}) if return_meta else False
    else:
        if p2 >= p0:
            return (False, {}) if return_meta else False

    # wave3 not shortest
    w1 = _abs_move(mws[0])
    w3 = _abs_move(mws[2])
    w5 = _abs_move(mws[4])
    if w3 <= min(w1, w5):
        return (False, {}) if return_meta else False

    # wave4 overlap heuristic
    # Uptrend: wave4 low should not go below wave1 high (common rule). We'll only flag.
    if s == 1:
        meta["w4_overlap"] = bool(p4 < p1)
    else:
        meta["w4_overlap"] = bool(p4 > p1)

    return (True, meta) if return_meta else True
