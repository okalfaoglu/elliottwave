"""Simple pattern-based backtest (M1.7).

Improvements:
- Optional bar-based pricing (more realistic than using pattern pivot prices):
    entry/exit taken from bars close at leg1.start_idx / leg5.end_idx.
- Fees + slippage (in bps) applied on entry and exit.
- Extra metrics: profit factor, expectancy, Sharpe-like (trade-return mean/std).

Notes:
- Index mapping assumes pattern leg indices align with bar index order. For our pipeline
  (bars -> zigzag -> swings -> monowaves -> patterns) this is typically true when
  zigzag returns indices in bar space.
"""

from __future__ import annotations

from dataclasses import dataclass

from ew6.logging import get_logger

log = get_logger("ew6.backtest")
from typing import List, Tuple, Optional
import math


@dataclass(frozen=True)
class Trade:
    pattern_idx: int
    direction: int  # +1 long, -1 short
    entry_px: float
    exit_px: float
    ret: float       # signed return after costs
    pnl: float       # cash PnL
    equity_after: float
    fees: float
    slippage: float


@dataclass(frozen=True)
class BacktestReport:
    initial_cash: float
    final_equity: float
    trades: int
    wins: int
    winrate: float
    avg_ret: float
    total_ret: float
    max_drawdown: float  # fraction
    equity_curve: List[float]
    profit_factor: float
    expectancy: float
    sharpe_like: float


def _dd_from_curve(curve: List[float]) -> float:
    if not curve:
        return 0.0
    peak = curve[0]
    mdd = 0.0
    for x in curve:
        if x > peak:
            peak = x
        dd = (peak - x) / peak if peak > 0 else 0.0
        if dd > mdd:
            mdd = dd
    return mdd


def _close_at(bars, idx: int) -> Optional[float]:
    """Get close price at bar index idx."""
    try:
        df = bars.df
        if idx < 0:
            idx = 0
        if idx >= len(df):
            idx = len(df) - 1
        return float(df["close"].iloc[idx])
    except Exception:
        return None


def backtest_patterns(
    patterns,
    initial_cash: float = 10_000.0,
    risk_fraction: float = 1.0,
    min_confidence: float = 0.0,
    bars=None,
    entry_mode: str = "pattern",   # "pattern" or "bar"
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> Tuple[List[Trade], BacktestReport]:
    equity = float(initial_cash)
    curve = [equity]
    trades: List[Trade] = []
    log.debug("backtest start", extra={"patterns": len(patterns), "bars": len(bars) if hasattr(bars,'__len__') else None, "fee_bps": fee_bps, "slippage_bps": slippage_bps, "entry_mode": entry_mode})
    wins = 0
    rets = []
    gross_wins = 0.0
    gross_losses = 0.0

    fb = float(fee_bps) / 10_000.0
    sb = float(slippage_bps) / 10_000.0

    for i, p in enumerate(patterns):
        meta = getattr(p, "meta", {}) or {}
        conf = float(meta.get("confidence", 0.0))
        if conf < float(min_confidence):
            continue
        legs = getattr(p, "legs", None) or []
        if len(legs) < 5:
            continue

        # Determine direction from leg1
        direction = 1 if (float(legs[0].end_px) - float(legs[0].start_px)) >= 0 else -1

        if entry_mode == "bar" and bars is not None:
            e = _close_at(bars, int(legs[0].start_idx))
            x = _close_at(bars, int(legs[-1].end_idx))
            if e is None or x is None:
                entry = float(legs[0].start_px)
                exitp = float(legs[-1].end_px)
            else:
                entry, exitp = float(e), float(x)
        else:
            entry = float(legs[0].start_px)
            exitp = float(legs[-1].end_px)

        if entry <= 0 or exitp <= 0:
            continue

        gross_ret = (exitp - entry) / entry
        signed_gross = gross_ret if direction == 1 else -gross_ret

        # Costs: fee + slippage on entry and exit, proportional
        # Approx: total cost fraction = 2*(fee + slippage)
        cost_frac = 2.0 * (fb + sb)
        signed_net = signed_gross - cost_frac

        stake = equity * float(risk_fraction)
        pnl = stake * signed_net
        equity2 = equity + pnl

        fees = stake * (2.0 * fb)
        slip = stake * (2.0 * sb)

        t = Trade(
            pattern_idx=i,
            direction=direction,
            entry_px=entry,
            exit_px=exitp,
            ret=signed_net,
            pnl=pnl,
            equity_after=equity2,
            fees=fees,
            slippage=slip,
        )
        trades.append(t)
        equity = equity2
        curve.append(equity)
        rets.append(signed_net)

        if signed_net > 0:
            wins += 1
            gross_wins += signed_net
        else:
            gross_losses += -signed_net

    total_ret = (equity - initial_cash) / initial_cash if initial_cash > 0 else 0.0
    avg_ret = sum(rets) / len(rets) if rets else 0.0
    winrate = wins / len(trades) if trades else 0.0
    mdd = _dd_from_curve(curve)

    profit_factor = (gross_wins / gross_losses) if gross_losses > 1e-12 else (float("inf") if gross_wins > 0 else 0.0)
    expectancy = avg_ret
    # Sharpe-like: mean/std of trade returns (not annualized)
    if len(rets) >= 2:
        mu = avg_ret
        var = sum((x - mu) ** 2 for x in rets) / (len(rets) - 1)
        sd = math.sqrt(var) if var > 0 else 0.0
        sharpe_like = (mu / sd) if sd > 1e-12 else (float("inf") if mu > 0 else 0.0)
    else:
        sharpe_like = 0.0

    rep = BacktestReport(
        initial_cash=float(initial_cash),
        final_equity=float(equity),
        trades=len(trades),
        wins=wins,
        winrate=float(winrate),
        avg_ret=float(avg_ret),
        total_ret=float(total_ret),
        max_drawdown=float(mdd),
        equity_curve=curve,
        profit_factor=float(profit_factor) if profit_factor != float("inf") else float("inf"),
        expectancy=float(expectancy),
        sharpe_like=float(sharpe_like) if sharpe_like != float("inf") else float("inf"),
    )
    return trades, rep
