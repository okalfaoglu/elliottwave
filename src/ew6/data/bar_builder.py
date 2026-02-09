from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from .types import BarSeries

TimeFreq = Literal["1min", "5min", "15min", "30min", "1h", "4h", "1d"]


@dataclass(frozen=True)
class TimeBarConfig:
    """Time-based bars (e.g., 5min)."""
    freq: TimeFreq = "5min"


@dataclass(frozen=True)
class TickBarConfig:
    """Tick-count bars (e.g., 50T = 50 ticks per bar)."""
    ticks_per_bar: int = 50


def resample_to_time_bars(df_ticks: pd.DataFrame, cfg: TimeBarConfig) -> BarSeries:
    """Resample ticks to time-based OHLC(V) bars.

    Expects df_ticks.index as DatetimeIndex and a 'price' column. If 'size' exists,
    it is used as volume.
    """
    if not isinstance(df_ticks.index, pd.DatetimeIndex):
        raise TypeError("df_ticks.index must be a pandas.DatetimeIndex")
    if "price" not in df_ticks.columns:
        raise ValueError("df_ticks must contain a 'price' column")

    px = df_ticks["price"].resample(cfg.freq)
    out = pd.DataFrame(
        {
            "open": px.first(),
            "high": px.max(),
            "low": px.min(),
            "close": px.last(),
        }
    )
    if "size" in df_ticks.columns:
        out["volume"] = df_ticks["size"].resample(cfg.freq).sum()
    out = out.dropna(subset=["open", "high", "low", "close"])
    return BarSeries(out)


def build_tick_bars(df_ticks: pd.DataFrame, cfg: TickBarConfig) -> BarSeries:
    """Aggregate ticks into fixed-tick-count OHLC(V) bars (e.g., 50T).

    Bar timestamp is the timestamp of the last tick in the bar.
    """
    if cfg.ticks_per_bar <= 0:
        raise ValueError("ticks_per_bar must be > 0")
    if not isinstance(df_ticks.index, pd.DatetimeIndex):
        raise TypeError("df_ticks.index must be a pandas.DatetimeIndex")
    if "price" not in df_ticks.columns:
        raise ValueError("df_ticks must contain a 'price' column")

    df = df_ticks.sort_index()
    n = len(df)
    if n == 0:
        return BarSeries(pd.DataFrame(columns=["open","high","low","close","volume"]))

    # assign group id per tick count
    grp = (pd.Series(range(n), index=df.index) // cfg.ticks_per_bar).astype(int)
    g = df.groupby(grp)

    out = pd.DataFrame(
        {
            "open": g["price"].first(),
            "high": g["price"].max(),
            "low": g["price"].min(),
            "close": g["price"].last(),
        }
    )
    if "size" in df.columns:
        out["volume"] = g["size"].sum()
    else:
        out["volume"] = 0.0

    # timestamp = last tick timestamp in each group
    out.index = g.apply(lambda x: x.index[-1])
    out.index.name = "ts"
    out = out.dropna(subset=["open", "high", "low", "close"])
    return BarSeries(out)
