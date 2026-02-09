# PROJECT_SPEC_v1.1 ADDENDUM — Bar Construction Modes (LOCKED-ADDENDUM)

This addendum extends **PROJECT_SPEC_v1.md (v1.0 LOCKED)** without modifying it.

## What changed
EW6 now supports **two bar construction modes** when ingesting tick data:

1) **Time bars** (default): `--bar_type time --timeframe 5min`
2) **Tick-count bars**: `--bar_type tick --ticks_per_bar 50` (e.g., 50T)

Downstream modules (`swing/`, `ew/`, `signals/`, `backtest/`) remain **bar-type agnostic** and operate on `BarSeries`.

## CLI contract
Exactly one of:
- `--bars <path>`: already-binned OHLC(V) bars CSV
- `--ticks <path>`: tick CSV (`timestamp + price [+ size]`)

When `--ticks` is used:
- `--bar_type` in `{time,tick}` (default: `time`)
- `--timeframe` (default: `5min`) for time bars
- `--ticks_per_bar` (default: `50`) for tick bars

## Tick CSV expectations
- Timestamp column: one of `ts,timestamp,date,datetime,time`
- Price column: `price` (or alternatives auto-mapped: `last,trade_price,px,close`)
- Optional size/volume: `size` (or alternatives auto-mapped: `qty,quantity,volume`)
