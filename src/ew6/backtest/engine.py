from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd

from ew6.data.types import BarSeries
from ew6.signals.generator import Signal, Side


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 10_000.0
    allow_short: bool = False
    max_position_pct: float = 1.0  # 1.0 = 100% notional allocation when going long


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: List[dict]


def run_simple_backtest(bars: BarSeries, signals: List[Signal], cfg: BacktestConfig) -> BacktestResult:
    """Toy backtest: apply the first non-FLAT signal at start and mark-to-market to end.

    Defaults to long-only (no short) to avoid misleading equity blow-ups.
    This is intentionally simple; the event-driven engine comes in M2.
    """
    bars.validate()
    close = bars.close
    equity = pd.Series(index=close.index, dtype=float)

    cash = float(cfg.initial_cash)
    pos_qty = 0.0
    trades: List[dict] = []

    # Apply first actionable signal at the first bar.
    if signals:
        sig = next((s for s in signals if s.side != Side.FLAT), None)
        if sig is not None:
            entry_price = float(close.iloc[0])
            if sig.side == Side.BUY:
                notional = cash * float(cfg.max_position_pct)
                pos_qty = notional / entry_price
                cash -= notional
                trades.append({"side": "buy", "ts": close.index[0], "price": entry_price, "qty": pos_qty})
            elif sig.side == Side.SELL:
                if cfg.allow_short:
                    notional = cash * float(cfg.max_position_pct)
                    pos_qty = -notional / entry_price
                    trades.append({"side": "sell_short", "ts": close.index[0], "price": entry_price, "qty": pos_qty})
                else:
                    trades.append({"side": "sell_ignored_long_only", "ts": close.index[0], "price": entry_price, "qty": 0.0})

    for ts, price in close.items():
        equity.loc[ts] = cash + pos_qty * float(price)

    return BacktestResult(equity_curve=equity, trades=trades)
