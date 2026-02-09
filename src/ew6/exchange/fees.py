"""Fee schedule helpers.

Goal (M1.7):
- Provide a simple venue/market fee schedule to avoid hardcoding `--fee_bps` for every run.
- Keep it overrideable via CLI for your own VIP tier / fee discounts.

This is NOT meant to be perfect or account-specific.
It's a pragmatic default table to reduce friction.

All values are in **basis points** (bps), where 1 bps = 0.01%.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeeSchedule:
    maker_bps: float
    taker_bps: float


# Conservative defaults (may differ by account/tier/discounts).
_DEFAULTS: dict[tuple[str, str], FeeSchedule] = {
    ("binance", "spot"): FeeSchedule(maker_bps=10.0, taker_bps=10.0),     # ~0.10%
    ("binance", "futures"): FeeSchedule(maker_bps=2.0, taker_bps=4.0),   # ~0.02% / 0.04%
}


def get_fee_schedule(venue: str, market: str) -> FeeSchedule | None:
    key = (venue.strip().lower(), market.strip().lower())
    return _DEFAULTS.get(key)


def get_fee_bps(venue: str, market: str, side: str = "taker") -> float:
    """Return fee bps for venue+market.

    side: "taker" or "maker" (defaults to taker; backtest assumes market orders by default).
    """
    fs = get_fee_schedule(venue, market)
    if fs is None:
        return 0.0
    s = side.strip().lower()
    if s.startswith("m") and s != "taker":
        return float(fs.maker_bps)
    return float(fs.taker_bps)
