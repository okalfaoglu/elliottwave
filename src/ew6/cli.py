"""EW6 CLI (stabilized).

This CLI is intentionally defensive across scaffold versions:
- Does NOT depend on ew6.run.batch.run_job() signature.
- Loads bars from Binance (OHLCV or aggTrades->bars).
- Extracts swings via ew6.swing.zigzag adapters.
- Detects impulses via ew6.ew.detectors.analyzer
- Optional tuning via ew6.ew.detectors.tuner
- Optional backtest via ew6.backtest.simple.backtest_patterns (supports both return orders)
- Optional walk-forward via ew6.run.walkforward.walk_forward_metrics (stability/expanding/rolling)

Goal: eliminate syntax/indent regressions and signature mismatches.
"""

from __future__ import annotations














import argparse
import json
import os
import signal
import faulthandler
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from ew6.config import load_config
from ew6.logging import setup_logging, get_logger, LogConfig

log = get_logger("ew6.cli")


# ----------------------------- helpers -----------------------------

def _parse_csv_list(s: Optional[str]) -> List[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def _ensure_dir(p: str) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)


def _to_df(bars: Any) -> pd.DataFrame:
    """Convert BarSeries/list/df into a pandas DataFrame with ts/open/high/low/close/volume."""
    if bars is None:
        return pd.DataFrame()
    if isinstance(bars, pd.DataFrame):
        return bars.copy()
    # BarSeries style
    if hasattr(bars, "to_df"):
        try:
            df = bars.to_df()  # type: ignore
            if isinstance(df, pd.DataFrame):
                return df.copy()
        except Exception:
            pass
    # list of objects/dicts
    if isinstance(bars, (list, tuple)):
        if not bars:
            return pd.DataFrame()
        row0 = bars[0]
        if isinstance(row0, dict):
            df = pd.DataFrame(list(bars))
            return df
        # object with attributes
        rows = []
        for b in bars:
            rows.append({
                "ts": getattr(b, "ts", None),
                "open": getattr(b, "open", None),
                "high": getattr(b, "high", None),
                "low": getattr(b, "low", None),
                "close": getattr(b, "close", None),
                "volume": getattr(b, "volume", None),
            })
        return pd.DataFrame(rows)
    return pd.DataFrame()


def _bars_range_str(bars: Any) -> str:
    # Prefer BarSeries start/end if present
    if hasattr(bars, "start_time") and hasattr(bars, "end_time"):
        try:
            return f"[{getattr(bars,'start_time')}..{getattr(bars,'end_time')}]"
        except Exception:
            pass
    df = _to_df(bars)
    if df.empty:
        return "[None..None]"
    ts = None
    if "ts" in df.columns:
        ts = df["ts"]
    elif "timestamp" in df.columns:
        ts = df["timestamp"]
    if ts is None:
        return "[None..None]"
    try:
        t0 = int(ts.iloc[0])
        t1 = int(ts.iloc[-1])
        return f"[{pd.to_datetime(t0, unit='ms', utc=True)}..{pd.to_datetime(t1, unit='ms', utc=True)}]"
    except Exception:
        return "[None..None]"


def _bt_call(backtest_patterns_fn, patterns: Any, bars: Any, btkw: Dict[str, Any]) -> Tuple[Any, Any]:
    """Support both (rep, trades) and (trades, rep) return orders."""
    out = backtest_patterns_fn(patterns, bars=bars, **btkw)
    if not isinstance(out, (list, tuple)) or len(out) != 2:
        return out, None
    a, b = out
    # Heuristic: report has attributes like total_return/final_equity
    if hasattr(a, "total_return") or hasattr(a, "final_equity") or hasattr(a, "total_ret"):
        return a, b
    if hasattr(b, "total_return") or hasattr(b, "final_equity") or hasattr(b, "total_ret"):
        return b, a
    # fallback
    return a, b


@dataclass
class JobResult:
    symbol: str
    timeframe: str
    bars: int
    swings: int
    patterns: int
    best_score: float
    best_conf: float
    tuned: int = 0

    bt_trades: int = 0
    bt_winrate: float = 0.0
    bt_mdd: float = 0.0
    bt_totalret: float = 0.0
    bt_equity: float = 0.0
    bt_pf: float = 0.0
    bt_sharpe: float = 0.0

    wf_mode: str = ""
    wf_splits: float = 0.0
    wf_score: float = 0.0
    wf_pos: float = 0.0
    wf_ret_mu: float = 0.0
    wf_ret_sd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


# ------------------------- Binance loading --------------------------

@dataclass
class _OHLCVReq:
    instrument: Any
    timeframe: str = "5m"
    limit: int = 1000
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None


@dataclass
class _TradesReq:
    instrument: Any
    limit: int = 1000
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None
    lookback_hours: float = 72.0
    max_records: int = 200_000


def _make_instrument(symbol: str, market: str, venue: str = "binance") -> Any:
    # Instrument model differs across scaffolds.
    try:
        from ew6.exchange.types import Instrument  # type: ignore
        try:
            return Instrument(symbol=symbol, market=market, venue=venue)
        except TypeError:
            return Instrument(symbol=symbol, market=market)
    except Exception:
        # fallback: simple object
        return type("Instrument", (), {"symbol": symbol, "market": market, "venue": venue})()


def _binance_connector(progress: bool = False):
    from ew6.exchange.binance.connector import BinanceConnector, BinanceConfig  # type: ignore
    try:
        cfg = BinanceConfig(progress=progress)
    except TypeError:
        cfg = BinanceConfig()
    return BinanceConnector(cfg)


def _trades_to_time_bars(trades: List[Dict[str, Any]], timeframe: str) -> Any:
    # timeframe like "5m", "1m", "15m"
    tf = timeframe.strip().lower()
    if tf.endswith("min"):
        tf = tf[:-3] + "m"
    if not tf.endswith("m"):
        raise ValueError("Only minute timeframes supported for trade time bars in this CLI")
    minutes = int(tf[:-1])
    if minutes <= 0:
        minutes = 5

    if not trades:
        return []

    # Binance aggTrades keys: T (ms), p (price), q (qty)
    rows = []
    for t in trades:
        ts = t.get("T") or t.get("time") or t.get("ts") or t.get("timestamp")
        px = t.get("p") or t.get("price") or t.get("c")
        qty = t.get("q") or t.get("qty") or t.get("volume") or 0.0
        if ts is None or px is None:
            continue
        rows.append((int(ts), float(px), float(qty)))
    if not rows:
        return []

    df = pd.DataFrame(rows, columns=["ts", "price", "qty"])
    # floor to timeframe bucket
    bucket = (df["ts"] // (minutes * 60_000)) * (minutes * 60_000)
    df["bucket"] = bucket

    g = df.groupby("bucket", sort=True)
    out = pd.DataFrame({
        "ts": g["bucket"].first(),
        "open": g["price"].first(),
        "high": g["price"].max(),
        "low": g["price"].min(),
        "close": g["price"].last(),
        "volume": g["qty"].sum(),
    }).reset_index(drop=True)

    # Return BarSeries if available
    try:
        from ew6.data.bars import Bar, BarSeries  # type: ignore
        bars = [Bar(ts=int(r.ts), open=float(r.open), high=float(r.high), low=float(r.low), close=float(r.close), volume=float(r.volume))
                for r in out.itertuples(index=False)]
        return BarSeries.from_bars(bars)
    except Exception:
        return out


def _trades_to_tick_bars(trades: List[Dict[str, Any]], ticks_per_bar: int) -> Any:
    n = max(1, int(ticks_per_bar))
    if not trades:
        return []

    rows = []
    for t in trades:
        ts = t.get("T") or t.get("time") or t.get("ts") or t.get("timestamp")
        px = t.get("p") or t.get("price") or t.get("c")
        qty = t.get("q") or t.get("qty") or t.get("volume") or 0.0
        if ts is None or px is None:
            continue
        rows.append((int(ts), float(px), float(qty)))
    if not rows:
        return []

    # chunk by ticks_per_bar
    out_rows = []
    for i in range(0, len(rows), n):
        chunk = rows[i:i+n]
        if not chunk:
            continue
        ts0 = chunk[0][0]
        prices = [c[1] for c in chunk]
        qtys = [c[2] for c in chunk]
        out_rows.append((ts0, prices[0], max(prices), min(prices), prices[-1], float(sum(qtys))))

    out = pd.DataFrame(out_rows, columns=["ts","open","high","low","close","volume"])
    try:
        from ew6.data.bars import Bar, BarSeries  # type: ignore
        bars = [Bar(ts=int(r.ts), open=float(r.open), high=float(r.high), low=float(r.low), close=float(r.close), volume=float(r.volume))
                for r in out.itertuples(index=False)]
        return BarSeries.from_bars(bars)
    except Exception:
        return out


def _load_from_binance(
    *,
    symbol: str,
    market: str,
    data: str,
    timeframe: str,
    lookback_hours: float,
    bar_type: str,
    ticks_per_bar: int,
    max_trades: int,
    progress: bool,
) -> Tuple[Any, Any]:
    conn = _binance_connector(progress=progress)
    inst = _make_instrument(symbol, market=str(market).lower(), venue="binance")

    if data.lower() == "ohlcv":
        req = _OHLCVReq(instrument=inst, timeframe=timeframe, limit=1000)
        bars = conn.fetch_ohlcv(req)
        return bars, conn

    # trades
    treq = _TradesReq(instrument=inst, limit=1000, lookback_hours=float(lookback_hours), max_records=int(max_trades or 200_000))
    trades = conn.fetch_trades(treq)
    if str(bar_type).lower() == "tick":
        bars = _trades_to_tick_bars(trades, ticks_per_bar=int(ticks_per_bar))
    else:
        bars = _trades_to_time_bars(trades, timeframe=timeframe)
    return bars, conn


# ----------------------- Swings / Analyzer --------------------------

def _extract_swings(bars: Any, pct: float) -> Any:
    from ew6.swing import zigzag as zz  # type: ignore

    # Config might exist
    ZigZagConfig = getattr(zz, "ZigZagConfig", None)
    cfg = ZigZagConfig(pct=float(pct)) if ZigZagConfig else None

    if hasattr(zz, "extract_swings"):
        return zz.extract_swings(bars, cfg) if cfg is not None else zz.extract_swings(bars, float(pct))

    # function variants returning a list of SwingPoint
    df = _to_df(bars)
    if df.empty:
        return []
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"] if "close" in df.columns else high

    if hasattr(zz, "zigzag_from_hl"):
        return zz.zigzag_from_hl(high, low, pct=float(pct))
    if hasattr(zz, "zigzag_from_close"):
        return zz.zigzag_from_close(close, pct=float(pct))

    raise RuntimeError("No swing extractor available in ew6.swing.zigzag")


def _detect_patterns(swings: Any, options: Any) -> Any:
    from ew6.ew.detectors.analyzer import AnalyzerConfig, scan_impulses_from_swings  # type: ignore

    # AnalyzerConfig variants
    try:
        ac = AnalyzerConfig.from_options(options)  # type: ignore
    except Exception:
        try:
            ac = AnalyzerConfig(options=options)  # type: ignore
        except Exception:
            ac = AnalyzerConfig()  # type: ignore
    out = scan_impulses_from_swings(swings, ac)
    # some versions return (patterns, best_score, best_conf)
    if isinstance(out, tuple) and len(out) >= 1:
        return out[0]
    return out


def _summarize_patterns(patterns: Any) -> Tuple[float, float]:
    if not patterns:
        return 0.0, 0.0
    # patterns with .meta dict
    try:
        best = max(patterns, key=lambda p: float(getattr(p, "meta", {}).get("score", 0.0)))
        meta = getattr(best, "meta", {}) or {}
        return float(meta.get("score", 0.0)), float(meta.get("confidence", 0.0))
    except Exception:
        return 0.0, 0.0


# ----------------------------- main -----------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ew6")

    # data source (binance only in M1)
    p.add_argument("--binance_symbol", default="", help="Single symbol (e.g., BTCUSDT)")
    p.add_argument("--symbols", default="", help="Comma-separated symbols for batch")
    p.add_argument("--timeframe", default="5m", help="Single timeframe (default 5m)")
    p.add_argument("--timeframes", default="", help="Comma-separated timeframes for batch")
    p.add_argument("--binance_market", default="futures", help="spot|futures")
    p.add_argument("--binance_data", default="ohlcv", help="ohlcv|trades")
    p.add_argument("--lookback_hours", type=float, default=72.0)
    p.add_argument("--bar_type", default="time", help="time|tick (only for trades)")
    p.add_argument("--ticks_per_bar", type=int, default=50)
    p.add_argument("--max_trades", type=int, default=200000)
    p.add_argument("--progress", action="store_true")

    # EW / backtest
    p.add_argument("--zigzag_pct", type=float, default=0.5)
    p.add_argument("--tune", action="store_true")
    p.add_argument("--min_confidence", type=float, default=0.0)

    p.add_argument("--backtest", action="store_true")
    p.add_argument("--entry_mode", default="pattern", help="pattern|bar")
    p.add_argument("--fee_bps", type=float, default=0.0)
    p.add_argument("--slippage_bps", type=float, default=0.0)

    # walk-forward
    p.add_argument("--walk_forward", action="store_true")
    p.add_argument("--wf_mode", default="stability", help="stability|expanding|rolling")
    p.add_argument("--wf_splits", type=int, default=3)
    p.add_argument("--wf_min_bars", type=int, default=200)
    p.add_argument("--wf_train_bars", type=int, default=0)
    p.add_argument("--wf_test_bars", type=int, default=0)
    p.add_argument("--wf_step_bars", type=int, default=0)

    # exports
    p.add_argument("--export_report", default="")
    p.add_argument("--export_report_csv", default="")
    p.add_argument("--export_reco", default="")
    p.add_argument("--export_trades", default="")

    # ranking
    p.add_argument("--rank_top", type=int, default=5)
    p.add_argument("--rank_oos_weight", type=float, default=0.60)

    # notify
    p.add_argument("--notify", action="store_true")
    p.add_argument("--notify_channels", default="", help="telegram,email")
    p.add_argument("--notify_format", default="compact", help="compact|pretty")

    # logging/config
    p.add_argument("--config", default=os.environ.get("EW6_CONFIG", ""))
    p.add_argument("--log_level", default=os.environ.get("EW6_LOG_LEVEL", "info"))

    return p


    from ew6.debug_stackdump import enable as _ew6_sd_enable
    _ew6_sd_enable()
def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    cfg = load_config(defaults={}, file_path=args.config or None)
    setup_logging(LogConfig(level=str(args.log_level)))

    # symbols/timeframes
    sym_list = _parse_csv_list(args.symbols)
    if args.binance_symbol:
        sym_list = [args.binance_symbol.strip()] + [s for s in sym_list if s != args.binance_symbol.strip()]
    if not sym_list:
        sym_list = ["BTCUSDT"]

    tf_list = _parse_csv_list(args.timeframes) or [args.timeframe.strip()]

    # options
    from ew6.ew.core.options import WaveOptions  # type: ignore
    opts = WaveOptions()

    # tuning
    tune_enabled = bool(args.tune)

    # backtest kwargs (filtering is inside backtest in most versions; we keep minimal)
    btkw: Dict[str, Any] = {
        "initial_cash": 10_000.0,
        "min_confidence": float(args.min_confidence),
        "entry_mode": str(args.entry_mode),
        "fee_bps": float(args.fee_bps),
        "slippage_bps": float(args.slippage_bps),
    }

    # import backtest
    from ew6.backtest.simple import backtest_patterns  # type: ignore

    # walk-forward
    from ew6.run.walkforward import walk_forward_metrics  # type: ignore

    # notify
    notify_channels = (args.notify_channels or str(cfg.get("notify_channels", ""))).strip()
    do_notify = bool(args.notify) and bool(notify_channels)

    # ranker
    from ew6.run.rank import rank_results  # type: ignore

    results: List[JobResult] = []
    reco_input: List[Tuple[str, str, Dict[str, Any]]] = []
    last_trades_any: Optional[Any] = None

    for sym in sym_list:
        for tf in tf_list:
            bars, conn = _load_from_binance(
                symbol=sym,
                market=args.binance_market,
                data=args.binance_data,
                timeframe=tf,
                lookback_hours=args.lookback_hours,
                bar_type=args.bar_type,
                ticks_per_bar=args.ticks_per_bar,
                max_trades=args.max_trades,
                progress=args.progress,
            )

            # swings
            swings = _extract_swings(bars, pct=float(args.zigzag_pct))

            # tune options using swings
            opts2 = opts
            tuned = 0
            if tune_enabled:
                try:
                    from ew6.ew.detectors.tuner import tune_wave_options  # type: ignore
                    tr = tune_wave_options(swings, opts)
                    opts2 = getattr(tr, "options", opts2)
                    tuned = 1
                except Exception as e:
                    log.warning("tune failed: %s", e)

            patterns = _detect_patterns(swings, opts2)
            best_score, best_conf = _summarize_patterns(patterns)

            # backtest
            bt_rep = None
            bt_trades = None
            if args.backtest:
                try:
                    bt_rep, bt_trades = _bt_call(backtest_patterns, patterns, bars, btkw)
                    last_trades_any = bt_trades
                except Exception as e:
                    log.error("backtest failed: %s", e)

            # walk-forward (only meaningful with backtest)
            wf: Dict[str, Any] = {}
            if args.walk_forward and args.backtest:
                try:
                    wf = walk_forward_metrics(
                        bars,
                        zigzag_pct=float(args.zigzag_pct),
                        options=opts2,
                        splits=int(args.wf_splits),
                        min_bars_per_split=int(args.wf_min_bars),
                        backtest_kwargs=btkw,
                        mode=str(args.wf_mode),
                        train_bars=(int(args.wf_train_bars) if int(args.wf_train_bars) > 0 else None),
                        test_bars=(int(args.wf_test_bars) if int(args.wf_test_bars) > 0 else None),
                        step_bars=(int(args.wf_step_bars) if int(args.wf_step_bars) > 0 else None),
                    )
                except Exception as e:
                    log.error("walk-forward failed: %s", e)

            jr = JobResult(
                symbol=sym,
                timeframe=tf,
                bars=int(len(bars) if hasattr(bars, "__len__") else 0),
                swings=int(len(swings) if hasattr(swings, "__len__") else 0),
                patterns=int(len(patterns) if hasattr(patterns, "__len__") else 0),
                best_score=float(best_score),
                best_conf=float(best_conf),
                tuned=int(tuned),
            )

            # fill backtest metrics
            if bt_rep is not None:
                # support multiple report field names across versions
                jr.bt_trades = int(getattr(bt_rep, "trades", getattr(bt_rep, "n_trades", 0)) or 0)
                jr.bt_winrate = float(getattr(bt_rep, "winrate", 0.0) or 0.0)
                jr.bt_mdd = float(getattr(bt_rep, "max_drawdown", getattr(bt_rep, "mdd", 0.0)) or 0.0)
                jr.bt_totalret = float(getattr(bt_rep, "total_return", getattr(bt_rep, "total_ret", 0.0)) or 0.0)
                jr.bt_equity = float(getattr(bt_rep, "final_equity", getattr(bt_rep, "equity_end", 0.0)) or 0.0)
                jr.bt_pf = float(getattr(bt_rep, "profit_factor", getattr(bt_rep, "pf", 0.0)) or 0.0)
                jr.bt_sharpe = float(getattr(bt_rep, "sharpe_like", getattr(bt_rep, "sharpe", 0.0)) or 0.0)

            # wf fields
            if wf:
                jr.wf_mode = str(args.wf_mode)
                jr.wf_splits = float(wf.get("wf_splits", wf.get("wf_splits_eff", 0)) or 0.0)
                jr.wf_score = float(wf.get("wf_score", 0.0) or 0.0)
                jr.wf_pos = float(wf.get("wf_pos_frac", wf.get("wf_pos", 0.0)) or 0.0)
                jr.wf_ret_mu = float(wf.get("wf_ret_mu", wf.get("wf_ret_mean", 0.0)) or 0.0)
                jr.wf_ret_sd = float(wf.get("wf_ret_sd", wf.get("wf_ret_std", 0.0)) or 0.0)

            results.append(jr)
            reco_input.append((jr.symbol, jr.timeframe, jr.to_dict()))

            # compact one-line
            rng = _bars_range_str(bars)
            print(
                f"symbol={jr.symbol} tf={jr.timeframe} bars={jr.bars} {rng} "
                f"swings={jr.swings} patterns={jr.patterns} best_score={jr.best_score:.2f} best_conf={jr.best_conf:.2f} "
                f"tuned={jr.tuned} "
                + (f"bt_trades={jr.bt_trades} bt_winrate={jr.bt_winrate:.2f} bt_mdd={jr.bt_mdd:.2f} bt_totalret={jr.bt_totalret:.2f} bt_equity={jr.bt_equity:.2f} bt_pf={jr.bt_pf:.2f} bt_sharpe={jr.bt_sharpe:.2f} " if args.backtest else "")
                + (f"wf_mode={jr.wf_mode} wf_score={jr.wf_score:.2f} wf_pos={jr.wf_pos:.2f} wf_ret_mu={jr.wf_ret_mu:.2f} wf_ret_sd={jr.wf_ret_sd:.2f}" if args.walk_forward and args.backtest else "")
            )

    # exports
    if args.export_report:
        _ensure_dir(args.export_report)
        with open(args.export_report, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in results], f, ensure_ascii=False, indent=2)

    if args.export_report_csv:
        _ensure_dir(args.export_report_csv)
        pd.DataFrame([r.to_dict() for r in results]).to_csv(args.export_report_csv, index=False)

    if args.export_trades and last_trades_any is not None:
        _ensure_dir(args.export_trades)
        try:
            # trades list of dicts
            if isinstance(last_trades_any, pd.DataFrame):
                last_trades_any.to_csv(args.export_trades, index=False)
            else:
                pd.DataFrame(list(last_trades_any)).to_csv(args.export_trades, index=False)
        except Exception as e:
            log.warning("export_trades failed: %s", e)

    ranked = rank_results(reco_input, top=int(args.rank_top), oos_weight=float(args.rank_oos_weight))
    print("recommendations=" + ", ".join([f"{x.symbol}:{x.timeframe}:{x.score:.3f}" for x in ranked]))
    if args.export_reco:
        _ensure_dir(args.export_reco)
        with open(args.export_reco, "w", encoding="utf-8") as f:
            json.dump([x.__dict__ for x in ranked], f, ensure_ascii=False, indent=2)

    # notifications (optional)
    if do_notify:
        try:
            from ew6.notify import notify_run  # type: ignore

            _notify_attachments: List[str] = []
            for _p in [args.export_report, args.export_report_csv, args.export_reco, args.export_trades]:
                if _p and os.path.exists(_p):
                    _notify_attachments.append(_p)

            _notify_title = f"EW6 Report ({','.join(sym_list)} | {','.join(tf_list)})"

            notify_run(
                results=[r.to_dict() for r in results],
                ranked=[x.__dict__ for x in ranked],
                channels=_parse_csv_list(notify_channels),
                fmt=str(args.notify_format),
                attachments=_notify_attachments,
                title=_notify_title,
            )
        except Exception as e:
            log.warning("notify failed: %s", e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
