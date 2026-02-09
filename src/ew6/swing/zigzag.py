"""ZigZag / swing extraction.

This project went through multiple iterations; some parts expect:
- zigzag_swings(bars, ZigZagConfig)  OR
- extract_swings(bars, cfg)         OR
- zigzag_from_hl(high, low, pct) / zigzag_from_close(close, pct)

This module provides a *stable adapter API*:
- ZigZagConfig(pct=...)
- extract_swings(bars_or_df, cfg_or_pct)
- zigzag_swings(bars_or_df, cfg_or_pct)  (alias)

If you already have implementations `zigzag_from_hl` and `zigzag_from_close` in your version,
keep them below; the adapter will call them if present.

The returned swings are normalized to a list of tuples: (idx:int, price:float).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Sequence, Tuple, Optional

import pandas as pd


# -------------------------
# Stable config
# -------------------------
@dataclass(frozen=True)
class ZigZagConfig:
    pct: float = 1.0


# -------------------------
# Helpers
# -------------------------
def _bars_to_df(bars: Any) -> pd.DataFrame:
    """Best-effort conversion of BarSeries-like object to DataFrame with OHLCV."""
    if isinstance(bars, pd.DataFrame):
        return bars
    if hasattr(bars, "df") and isinstance(getattr(bars, "df"), pd.DataFrame):
        return bars.df
    if hasattr(bars, "to_df"):
        df = bars.to_df()
        if isinstance(df, pd.DataFrame):
            return df

    # fallback: assume iterable of bar objects with open/high/low/close/volume
    rows = []
    idx = []
    seq = getattr(bars, "bars", None)
    if seq is None:
        try:
            seq = list(bars)
        except TypeError:
            seq = []
    for i, b in enumerate(seq):
        t = getattr(b, "ts", None) or getattr(b, "time", None) or getattr(b, "timestamp", None)
        if t is None:
            t = i
        idx.append(t)
        rows.append(
            (
                getattr(b, "open", None),
                getattr(b, "high", None),
                getattr(b, "low", None),
                getattr(b, "close", None),
                getattr(b, "volume", None),
            )
        )
    return pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"], index=pd.Index(idx, name="time"))


def _get_pct(cfg_or_pct: Any) -> float:
    if isinstance(cfg_or_pct, (int, float)):
        return float(cfg_or_pct)
    if isinstance(cfg_or_pct, dict) and "pct" in cfg_or_pct:
        return float(cfg_or_pct["pct"])
    if hasattr(cfg_or_pct, "pct"):
        return float(getattr(cfg_or_pct, "pct"))
    return 1.0


def _normalize_swings(swings: Any) -> List[Tuple[int, float]]:
    """Normalize many possible swing formats to list[(idx, price)]."""
    if swings is None:
        return []
    # If it's a DataFrame, try columns
    if isinstance(swings, pd.DataFrame):
        for a, b in (("idx", "price"), ("index", "price"), ("idx", "px"), ("index", "px")):
            if a in swings.columns and b in swings.columns:
                return [(int(i), float(p)) for i, p in zip(swings[a].tolist(), swings[b].tolist())]
        # fallback: use index as idx, first numeric column as price
        cols = [c for c in swings.columns if pd.api.types.is_numeric_dtype(swings[c])]
        if cols:
            return [(int(i), float(swings.iloc[k][cols[0]])) for k, i in enumerate(swings.index)]
        return []

    # If it's (idxs, prices)
    if isinstance(swings, (tuple, list)) and len(swings) == 2 and all(hasattr(x, "__len__") for x in swings):
        a, b = swings
        try:
            return [(int(i), float(p)) for i, p in zip(a, b)]
        except Exception:
            pass

    out: List[Tuple[int, float]] = []
    try:
        it = list(swings)
    except Exception:
        return out

    for sp in it:
        # tuple/list
        if isinstance(sp, (tuple, list)) and len(sp) >= 2:
            out.append((int(sp[0]), float(sp[1])))
            continue
        # dict
        if isinstance(sp, dict):
            idx = sp.get("idx", sp.get("index"))
            px = sp.get("price", sp.get("px", sp.get("value")))
            if idx is not None and px is not None:
                out.append((int(idx), float(px)))
            continue
        # object attrs
        idx = None
        px = None
        for ik in ("idx", "index"):
            if hasattr(sp, ik):
                idx = getattr(sp, ik)
                break
        for pk in ("price", "px", "value"):
            if hasattr(sp, pk):
                px = getattr(sp, pk)
                break
        if idx is not None and px is not None:
            out.append((int(idx), float(px)))

    return out


# -------------------------
# Adapter API
# -------------------------
def extract_swings(bars_or_df: Any, cfg_or_pct: Any = None) -> List[Tuple[int, float]]:
    """Extract swings using the best available implementation and normalize format."""
    pct = _get_pct(cfg_or_pct) if cfg_or_pct is not None else 1.0
    df = _bars_to_df(bars_or_df)

    # Prefer HL zigzag when available
    fn_hl = globals().get("zigzag_from_hl", None)
    if callable(fn_hl) and "high" in df.columns and "low" in df.columns:
        hi = df["high"]
        lo = df["low"]
        for args in ((hi, lo, pct), (hi, lo, float(pct))):
            try:
                swings = fn_hl(*args)
                norm = _normalize_swings(swings)
                if len(norm) >= 2:
                    return norm
            except Exception:
                continue

    fn_c = globals().get("zigzag_from_close", None)
    if callable(fn_c) and "close" in df.columns:
        cl = df["close"]
        for args in ((cl, pct), (cl, float(pct))):
            try:
                swings = fn_c(*args)
                norm = _normalize_swings(swings)
                if len(norm) >= 2:
                    return norm
            except Exception:
                continue

    # last resort: look for any callable with 'zigzag' in name
    for name, obj in list(globals().items()):
        if not callable(obj):
            continue
        lname = str(name).lower()
        if "zigzag" not in lname and "swing" not in lname:
            continue
        for args in ((df, pct), (df,), (bars_or_df, pct), (bars_or_df,)):
            try:
                swings = obj(*args)
                norm = _normalize_swings(swings)
                if len(norm) >= 2:
                    return norm
            except Exception:
                continue

    raise ImportError("No usable zigzag implementation found (expected zigzag_from_hl or zigzag_from_close).")


def zigzag_swings(bars_or_df: Any, cfg_or_pct: Any = None) -> List[Tuple[int, float]]:
    return extract_swings(bars_or_df, cfg_or_pct)


# -------------------------
# Optional: legacy implementations (if your repo already has them, keep yours)
# -------------------------
# def zigzag_from_close(close: pd.Series, pct: float): ...
# def zigzag_from_hl(high: pd.Series, low: pd.Series, pct: float): ...
