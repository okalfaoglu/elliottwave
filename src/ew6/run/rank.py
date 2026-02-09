from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class RankedItem:
    symbol: str
    timeframe: str
    score: float
    meta: Dict[str, Any]


def _get(m: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        v = m.get(key, default)
        if v is None:
            return float(default)
        return float(v)
    except Exception:
        return float(default)


def composite_score(meta: Dict[str, Any], *, oos_weight: float = 0.60) -> float:
    """Compute a single ranking score in [0,1] (heuristic).

    In-sample components:
      - bt_totalret (return)
      - bt_mdd (drawdown)
      - bt_pf (profit factor)
      - bt_sharpe

    Out-of-sample component (if present):
      - wf_score (walk-forward robustness score, already in [0,1])

    score = (1-oos_weight) * in_sample + oos_weight * wf_score  (if wf_score exists)
    Otherwise score = in_sample.

    oos_weight default 0.60 (prefer robustness).
    """
    # --- in-sample ---
    ret = max(0.0, _get(meta, "bt_totalret", 0.0))  # negative returns -> 0
    mdd = max(0.0, _get(meta, "bt_mdd", 0.0))
    pf = max(0.0, _get(meta, "bt_pf", 0.0))
    sh = _get(meta, "bt_sharpe", 0.0)

    # squashing functions (keep stable)
    import math
    s_ret = 1.0 - math.exp(-2.0 * ret)            # 0..1
    s_mdd = 1.0 / (1.0 + 10.0 * mdd)              # smaller mdd better
    s_pf = 1.0 - math.exp(-0.15 * min(pf, 40.0))  # saturate
    s_sh  = 1.0 / (1.0 + math.exp(-1.2 * sh))     # logistic

    in_sample = float(0.35 * s_ret + 0.25 * s_mdd + 0.25 * s_pf + 0.15 * s_sh)

    # --- out-of-sample ---
    wf = meta.get("wf_score", None)
    if wf is None:
        return float(in_sample)

    try:
        wf_score = float(wf)
    except Exception:
        wf_score = 0.0
    wf_score = max(0.0, min(1.0, wf_score))

    ow = max(0.0, min(1.0, float(oos_weight)))
    return float((1.0 - ow) * in_sample + ow * wf_score)


def rank_results(
    results: Iterable[Tuple[str, str, Dict[str, Any]]],
    *,
    top: int = 5,
    oos_weight: float = 0.60,
) -> List[RankedItem]:
    """Rank (symbol,timeframe,meta) tuples."""
    items: List[RankedItem] = []
    for sym, tf, meta in results:
        sc = composite_score(meta, oos_weight=oos_weight)
        items.append(RankedItem(symbol=sym, timeframe=tf, score=sc, meta=meta))
    items.sort(key=lambda x: x.score, reverse=True)
    return items[: max(0, int(top))]
