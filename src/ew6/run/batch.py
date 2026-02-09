"""Batch runner for EW6 (M1.10).

Enhancements:
- Optional walk-forward stability metrics (wf_*).
- Returns structured JobResult including wf metrics for report export + ranking.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

from ew6.logging import get_logger

from ew6.swing.zigzag import extract_swings, ZigZagConfig
from ew6.ew.core.options import WaveOptions
from ew6.ew.detectors.analyzer import AnalyzerConfig, scan_impulses_from_swings
from ew6.ew.detectors.tuner import tune_wave_options
from ew6.backtest.simple import backtest_patterns
from ew6.run.walkforward import walk_forward_metrics

log = get_logger("ew6.batch")


@dataclass(frozen=True)
class JobSpec:
    symbol: str
    market: str
    data_kind: str
    timeframe: str
    lookback_hours: int
    zigzag_pct: float
    bar_type: str = "time"
    ticks_per_bar: int = 50
    max_trades: int = 200_000


@dataclass
class JobResult:
    symbol: str
    timeframe: str
    bars: int
    swings: int
    patterns: int
    best_score: float
    best_conf: float
    tuned: bool

    bt_trades: int = 0
    bt_winrate: float = 0.0
    bt_mdd: float = 0.0
    bt_totalret: float = 0.0
    bt_equity: float = 0.0
    bt_pf: float = 0.0
    bt_sharpe: float = 0.0

    # Observability from connector (mainly trades)
    cap: str = ""
    pages: int = 0
    trades_records: int = 0

    # Walk-forward stability
    wf_splits: int = 0
    wf_pos_frac: float = 0.0
    wf_ret_mean: float = 0.0
    wf_ret_std: float = 0.0
    wf_mdd_mean: float = 0.0
    wf_trades_mean: float = 0.0
    wf_score: float = 0.0


def summarize_patterns(patterns) -> Tuple[float, float]:
    if not patterns:
        return 0.0, 0.0
    best = max(patterns, key=lambda p: float(p.meta.get("score", 0.0)))
    return float(best.meta.get("score", 0.0)), float(best.meta.get("confidence", 0.0))


def run_job(
    bars: Any,
    conn: Any,
    zigzag_pct: float,
    opts: WaveOptions,
    auto_tune: bool = False,
    backtest: bool = False,
    backtest_kwargs: Optional[Dict[str, Any]] = None,
    walk_forward: bool = False,
    wf_splits: int = 3,
    wf_min_bars: int = 200,
    wf_mode: str = "stability",
    wf_train_bars: int | None = None,
    wf_test_bars: int | None = None,
    wf_step_bars: int | None = None,
):
    log.debug("batch run_job start", extra={"bars": len(bars) if hasattr(bars,'__len__') else None, "zigzag_pct": zigzag_pct, "auto_tune": auto_tune, "backtest": backtest, "walk_forward": walk_forward, "wf_mode": wf_mode})
    swings = extract_swings(bars, ZigZagConfig(pct=zigzag_pct))
    tuned = False
    if auto_tune:
        tr = tune_wave_options(swings, opts)
        opts2 = tr.options
        tuned = True
    else:
        opts2 = opts

    patterns = scan_impulses_from_swings(swings, AnalyzerConfig.from_options(opts2))
    best_score, best_conf = summarize_patterns(patterns)

    bt = {}
    if backtest:
        kw = backtest_kwargs or {}
        out = backtest_patterns(patterns, bars=bars, **kw)
        if isinstance(out, (list, tuple)) and len(out) == 2:
            a, b = out
            # report detection heuristic
            rep = a if (hasattr(a, "total_return") or hasattr(a, "final_equity") or hasattr(a, "total_ret")) else b
            trades = b if rep is a else a
        else:
            rep, trades = out, None
        bt = {
            "bt_trades": int(getattr(rep, "trades", getattr(rep, "n_trades", 0)) or 0),
            "bt_winrate": float(getattr(rep, "winrate", 0.0) or 0.0),
            "bt_mdd": float(getattr(rep, "max_drawdown", getattr(rep, "mdd", 0.0)) or 0.0),
            "bt_totalret": float(getattr(rep, "total_return", getattr(rep, "total_ret", 0.0)) or 0.0),
            "bt_equity": float(getattr(rep, "final_equity", getattr(rep, "equity_end", 0.0)) or 0.0),
            "bt_pf": float(getattr(rep, "profit_factor", getattr(rep, "pf", 0.0)) or 0.0),
            "bt_sharpe": float(getattr(rep, "sharpe_like", getattr(rep, "sharpe", 0.0)) or 0.0),
        }
        log.debug("batch backtest", extra={"trades": bt.get("bt_trades"), "ret": bt.get("bt_totalret"), "mdd": bt.get("bt_mdd"), "pf": bt.get("bt_pf")})

    wf = {}
    if walk_forward and backtest:
        wf = walk_forward_metrics(
            bars,
            zigzag_pct=zigzag_pct,
            options=opts2,
            splits=int(wf_splits),
            min_bars_per_split=int(wf_min_bars),
            backtest_kwargs=(backtest_kwargs or {}),
            mode=str(wf_mode or "stability"),
            train_bars=(int(wf_train_bars) if wf_train_bars is not None else None),
            test_bars=(int(wf_test_bars) if wf_test_bars is not None else None),
            step_bars=(int(wf_step_bars) if wf_step_bars is not None else None),
        )

    meta = getattr(conn, "last_meta", None)
    obs = {}
    if meta is not None:
        obs = {
            "cap": getattr(meta, "cap_reason", ""),
            "pages": int(getattr(meta, "pages", 0) or 0),
            "trades_records": int(getattr(meta, "records", 0) or 0),
        }

    log.debug("batch run_job done", extra={"swings": len(swings) if hasattr(swings,'__len__') else None, "patterns": len(patterns) if hasattr(patterns,'__len__') else None, "best_score": best_score, "best_conf": best_conf, "tuned": tuned, "wf_score": wf.get("wf_score", 0.0) if isinstance(wf, dict) else 0.0})
    return swings, patterns, best_score, best_conf, tuned, bt, obs, wf


def to_dict(results: List[JobResult]) -> List[Dict[str, Any]]:
    return [asdict(r) for r in results]
