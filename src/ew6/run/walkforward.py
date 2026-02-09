"""Walk-forward evaluation (M1.8).

Modes
-----
- stability (legacy): slice into N contiguous segments and measure per-segment backtest return.
- expanding: expanding train window, forward test windows (OOS) with fixed test size.
- rolling: rolling train window (fixed size), forward test windows (OOS) with fixed test size.

Notes
-----
EW6 is not an ML model; we do not "fit" parameters. Walk-forward here is a robustness check:
does the same rule set behave consistently on out-of-sample segments?

Output keys (wf_*)
------------------
wf_splits, wf_pos_frac, wf_ret_mu, wf_ret_sd, wf_score
plus per-fold arrays: wf_fold_ret, wf_fold_start, wf_fold_end
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from ew6.swing.zigzag import extract_swings, ZigZagConfig
from ew6.ew.detectors.analyzer import AnalyzerConfig, scan_impulses_from_swings
from ew6.backtest.simple import backtest_patterns
from ew6.ew.core.options import WaveOptions

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore


def _clamp(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def _slice_to_barseries(bars: Any, i0: int, i1: int) -> Any:
    # Bars can be a list[Bar] or BarSeries (list-like). Keep same type if possible.
    if hasattr(bars, "slice"):
        return bars.slice(i0, i1)
    if isinstance(bars, list):
        return bars[i0:i1]
    try:
        return bars[i0:i1]  # type: ignore[index]
    except Exception:
        return list(bars)[i0:i1]


def _run_on_slice(
    bars_slice: Any,
    *,
    zigzag_pct: float,
    options: WaveOptions,
    backtest_kwargs: Dict[str, Any],
) -> float:
    # returns total return (as decimal, e.g. 0.12 for +12%)
    swings = extract_swings(bars_slice, ZigZagConfig(pct=zigzag_pct))
    patterns, _best_score, _best_conf = scan_impulses_from_swings(
        swings,
        AnalyzerConfig(options=options),
    )
    out = backtest_patterns(patterns, bars_slice, **backtest_kwargs)
    if isinstance(out, (list, tuple)) and len(out) == 2:
        a, b = out
        rep = a if (hasattr(a, "total_return") or hasattr(a, "final_equity") or hasattr(a, "total_ret")) else b
    else:
        rep = out
    return float(getattr(rep, "total_return", getattr(rep, "total_ret", 0.0)) or 0.0)


def _score(pos_frac: float, ret_mu: float, ret_sd: float) -> float:
    # simple, stable score in [0,1] (heuristic)
    # prefer positive consistency, higher mean return, lower volatility
    # clamp to avoid exploding due to tiny sd
    sd = max(ret_sd, 1e-9)
    sharpe_like = ret_mu / sd
    # squash
    import math
    s1 = 1 / (1 + math.exp(-3.0 * (pos_frac - 0.5)))  # centered at 0.5
    s2 = 1 / (1 + math.exp(-1.5 * sharpe_like))      # >0 better
    return float(0.55 * s1 + 0.45 * s2)


def walk_forward_metrics(
    bars: Any,
    *,
    zigzag_pct: float,
    options: WaveOptions,
    splits: int = 3,
    min_bars_per_split: int = 200,
    backtest_kwargs: Optional[Dict[str, Any]] = None,
    mode: str = "stability",
    train_bars: Optional[int] = None,
    test_bars: Optional[int] = None,
    step_bars: Optional[int] = None,
) -> Dict[str, Any]:
    """Compute walk-forward metrics.

    Parameters
    ----------
    mode:
      - stability: N contiguous segments, evaluate on each.
      - expanding: expanding train [0:train_end], test [train_end:train_end+test]
      - rolling: rolling train [train_end-train:test_end], test [train_end:test_end]
    train_bars/test_bars/step_bars:
      Used for expanding/rolling. If None, inferred from series length and splits.

    Returns
    -------
    dict with wf_* keys (see module docstring).
    """
    btkw = dict(backtest_kwargs or {})
    n = len(bars) if hasattr(bars, "__len__") else 0
    if n <= 0:
        return {"wf_splits": 0, "wf_pos_frac": 0.0, "wf_ret_mu": 0.0, "wf_ret_sd": 0.0, "wf_score": 0.0}

    splits = int(splits or 0)
    splits = _clamp(splits, 2, 20)

    mode = (mode or "stability").strip().lower()
    if mode not in ("stability", "expanding", "rolling"):
        mode = "stability"

    # infer sizes
    if test_bars is None:
        test_bars = max(int(n / splits), int(min_bars_per_split))
    test_bars = int(test_bars)
    step = int(step_bars) if step_bars is not None else test_bars
    step = max(1, step)

    if train_bars is None:
        # default: for rolling, 2x test; for expanding, min_bars
        train_bars = max(int(min_bars_per_split), int(2 * test_bars))
    train_bars = int(train_bars)

    fold_ret: List[float] = []
    fold_start: List[int] = []
    fold_end: List[int] = []

    if mode == "stability":
        # contiguous segments over full range
        seg = max(int(n / splits), int(min_bars_per_split))
        # recompute splits based on seg
        splits_eff = max(2, min(20, int(n / seg)))
        for k in range(splits_eff):
            i0 = k * seg
            i1 = min(n, (k + 1) * seg)
            if i1 - i0 < min_bars_per_split:
                continue
            r = _run_on_slice(_slice_to_barseries(bars, i0, i1), zigzag_pct=zigzag_pct, options=options, backtest_kwargs=btkw)
            fold_ret.append(r)
            fold_start.append(i0)
            fold_end.append(i1)
    else:
        # OOS folds
        # define initial train_end
        train_end = max(train_bars, min_bars_per_split)
        while True:
            test_start = train_end
            test_end = test_start + test_bars
            if test_end > n:
                break
            # (We compute on test only; train is present for semantics, but EW6 has no fitting yet.)
            r = _run_on_slice(_slice_to_barseries(bars, test_start, test_end), zigzag_pct=zigzag_pct, options=options, backtest_kwargs=btkw)
            fold_ret.append(r)
            fold_start.append(test_start)
            fold_end.append(test_end)

            train_end = train_end + step
            if mode == "rolling":
                # rolling window by moving train_end only (train_start implicit)
                # train size kept by semantics; currently unused.
                pass

    if not fold_ret:
        return {"wf_splits": 0, "wf_pos_frac": 0.0, "wf_ret_mu": 0.0, "wf_ret_sd": 0.0, "wf_score": 0.0, "wf_mode": mode}

    mu = sum(fold_ret) / len(fold_ret)
    # population stdev
    import math
    sd = math.sqrt(sum((x - mu) ** 2 for x in fold_ret) / len(fold_ret))
    pos = sum(1 for x in fold_ret if x > 0) / len(fold_ret)
    sc = _score(pos, mu, sd)

    return {
        "wf_mode": mode,
        "wf_splits": int(len(fold_ret)),
        "wf_pos_frac": float(pos),
        "wf_ret_mu": float(mu),
        "wf_ret_sd": float(sd),
        "wf_score": float(sc),
        "wf_fold_ret": fold_ret,
        "wf_fold_start": fold_start,
        "wf_fold_end": fold_end,
        "wf_test_bars": int(test_bars),
        "wf_train_bars": int(train_bars),
        "wf_step_bars": int(step),
    }
