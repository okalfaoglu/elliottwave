"""Binance connector (spot + futures) for OHLCV and aggTrades.

M1.7 goals:
- Disk cache (deterministic replay + faster batch)
- Simple retry/backoff for transient issues (429 / 5xx / "Internal error")

No third-party deps (requests); uses urllib.
"""

from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ew6.logging import get_logger

log = get_logger("ew6.binance")

from ew6.exchange.meta import FetchMeta
from ew6.exchange.types import Instrument


@dataclass(frozen=True)
class BinanceConfig:
    timeout_s: float = 10.0
    user_agent: str = "ew6/0.6"
    retry: int = 3
    retry_sleep_s: float = 0.35
    progress: bool = False

    # cache
    use_cache: bool = True
    cache_dir: str = ".cache/ew6/binance"
    cache_ttl_s: int = 0  # 0 => never expire


def _is_spot(market: Any) -> bool:
    v = None
    if hasattr(market, "value"):
        try:
            v = str(getattr(market, "value"))
        except Exception:
            v = None
    if v is None:
        v = str(market)
    v = v.lower()
    return "spot" in v


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _cache_path(cache_dir: str, url: str) -> Path:
    key = _sha256(url)
    return Path(cache_dir) / f"{key}.json"


def _cache_fresh(p: Path, ttl_s: int) -> bool:
    if not p.exists():
        return False
    if ttl_s <= 0:
        return True
    try:
        age = time.time() - p.stat().st_mtime
        return age <= float(ttl_s)
    except Exception:
        return False


class BinanceConnector:
    def __init__(self, cfg: BinanceConfig = BinanceConfig()):
        self.cfg = cfg
        self.last_meta: Optional[FetchMeta] = None

    def _base_url(self, market: Any) -> str:
        return "https://api.binance.com" if _is_spot(market) else "https://fapi.binance.com"

    def _get_json(self, base: str, path: str, params: Dict[str, Any]) -> Any:
        qs = urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{base}{path}?{qs}" if qs else f"{base}{path}"

        # --- cache read
        if self.cfg.use_cache and self.cfg.cache_dir:
            try:
                p = _cache_path(self.cfg.cache_dir, url)
                if _cache_fresh(p, int(self.cfg.cache_ttl_s)):
                    with p.open("r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception:
                pass

        # --- network fetch with retry/backoff
        last_err: Optional[Exception] = None
        for attempt in range(int(self.cfg.retry) + 1):
            req = Request(url, headers={"User-Agent": self.cfg.user_agent})
            try:
                with urlopen(req, timeout=float(self.cfg.timeout_s)) as resp:
                    raw = resp.read().decode("utf-8")
                    data = json.loads(raw)

                # cache write
                if self.cfg.use_cache and self.cfg.cache_dir:
                    try:
                        p = _cache_path(self.cfg.cache_dir, url)
                        p.parent.mkdir(parents=True, exist_ok=True)
                        tmp = p.with_suffix(p.suffix + ".tmp")
                        with tmp.open("w", encoding="utf-8") as f:
                            json.dump(data, f)
                        tmp.replace(p)
                    except Exception:
                        pass

                return data

            except HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8")
                except Exception:
                    body = ""

                # Retry only for transient-ish errors
                is_transient = (
                    e.code in (418, 429)
                    or 500 <= int(e.code) <= 599
                    or "internal error" in body.lower()
                )
                last_err = RuntimeError(f"Binance HTTP {e.code} for {url}. Body: {body}")
                if not is_transient or attempt >= int(self.cfg.retry):
                    raise last_err from e

            except URLError as e:
                last_err = e
                if attempt >= int(self.cfg.retry):
                    raise RuntimeError(f"Binance URLError for {url}: {e}") from e

            except Exception as e:
                last_err = e
                if attempt >= int(self.cfg.retry):
                    raise

            # Backoff before retry
            sleep_s = float(self.cfg.retry_sleep_s) * (2 ** attempt)
            if sleep_s > 3.0:
                sleep_s = 3.0
            time.sleep(sleep_s)

        # should not happen
        if last_err is not None:
            raise last_err
        raise RuntimeError("unknown error")

    # -------- OHLCV --------
    def fetch_ohlcv(self, req) -> Any:
        inst: Instrument = req.instrument if hasattr(req, "instrument") else req.inst
        timeframe = getattr(req, "timeframe", "5m")
        market = inst.market

        base = self._base_url(market)
        path = "/api/v3/klines" if _is_spot(market) else "/fapi/v1/klines"

        limit = getattr(req, "limit", 1000)
        start_ms = getattr(req, "start_ms", None)
        end_ms = getattr(req, "end_ms", None)

        params = {"symbol": inst.symbol, "interval": timeframe, "limit": limit, "startTime": start_ms, "endTime": end_ms}
        data = self._get_json(base, path, params)

        # Return BarSeries if available
        try:
            from ew6.data.bars import Bar, BarSeries  # type: ignore
            bars = []
            for k in data:
                bars.append(
                    Bar(
                        ts=int(k[0]),
                        open=float(k[1]),
                        high=float(k[2]),
                        low=float(k[3]),
                        close=float(k[4]),
                        volume=float(k[5]),
                    )
                )
            return BarSeries.from_bars(bars)
        except Exception:
            return data

    # -------- Trades / ticks --------
    def fetch_trades(self, req) -> List[Dict[str, Any]]:
        inst: Instrument = req.instrument if hasattr(req, "instrument") else req.inst
        market = inst.market
        base = self._base_url(market)

        path = "/api/v3/aggTrades" if _is_spot(market) else "/fapi/v1/aggTrades"

        limit = int(getattr(req, "limit", 1000) or 1000)
        max_records = int(getattr(req, "max_records", 200_000) or 200_000)

        start_ms = getattr(req, "start_ms", None)
        end_ms = getattr(req, "end_ms", None)

        if start_ms is None or end_ms is None:
            lookback_hours = getattr(req, "lookback_hours", 72)
            end_ms = int(time.time() * 1000)
            start_ms = end_ms - int(float(lookback_hours) * 3600 * 1000)

        meta = FetchMeta(
            venue="binance",
            market=str(getattr(market, "value", market)),
            kind="trades",
            requested_start_ms=int(start_ms),
            requested_end_ms=int(end_ms),
        )

        out: List[Dict[str, Any]] = []
        pages = 0
        cur_end = int(end_ms)

        retries_left = int(self.cfg.retry)

        while len(out) < max_records:
            params = {"symbol": inst.symbol, "limit": min(limit, max_records - len(out)), "endTime": cur_end}
            try:
                data = self._get_json(base, path, params)
            except RuntimeError as e:
                # for aggTrades, Binance sometimes returns 400 with body containing internal error;
                # _get_json retries already, but we also step back in time and keep going.
                if retries_left > 0:
                    retries_left -= 1
                    meta.notes = f"retry_after_error: {str(e)[:200]}"
                    time.sleep(float(self.cfg.retry_sleep_s))
                    cur_end -= 60_000
                    continue
                meta.cap_reason = "error"
                meta.notes = f"error: {str(e)[:250]}"
                break

            pages += 1
            if not isinstance(data, list) or len(data) == 0:
                meta.cap_reason = meta.cap_reason or "empty"
                break

            out.extend(data)

            try:
                times = [int(x.get("T")) for x in data if "T" in x]
                if times:
                    batch_min = min(times)
                    batch_max = max(times)
                    meta.earliest_ms = batch_min if meta.earliest_ms is None else min(meta.earliest_ms, batch_min)
                    meta.latest_ms = batch_max if meta.latest_ms is None else max(meta.latest_ms, batch_max)
                    cur_end = batch_min - 1
            except Exception:
                pass

            if meta.earliest_ms is not None and meta.earliest_ms <= int(start_ms):
                meta.cap_reason = meta.cap_reason or "start_reached"
                break

            if pages > 10_000:
                meta.cap_reason = meta.cap_reason or "max_pages"
                meta.notes = "hit max_pages safety"
                break

        try:
            out.sort(key=lambda x: int(x.get("T", 0)))
        except Exception:
            pass

        meta.records = len(out)
        meta.pages = pages
        if meta.cap_reason == "" and len(out) >= max_records:
            meta.cap_reason = "max_records"

        self.last_meta = meta
        return out
