# EW6 (Scaffold)

EW6 is a modular stack for:
Tick → Bar → Swing → Elliott Wave scan → Signals → Backtest/Trading.

This repo currently contains a **v0.1 scaffold**: the pipeline is wired end-to-end with placeholders where the full EW engine will be ported.

## Install (editable)
```bash
pip install -e .
```

Optional extras:
```bash
pip install -e .[fast,viz,ml]
```

## Quickstart

### A) Already-binned bars (OHLCV CSV)
Provide a bar CSV with a timestamp column (`ts`/`timestamp`/`date`/`datetime`) and columns `open,high,low,close` (volume optional).

```bash
ew6 --bars /path/to/bars.csv --zigzag_pct 2.0
```

### B) Tick CSV → bars (default: **5min**)
Tick CSV must include a timestamp column (`ts`/`timestamp`/`date`/`datetime`/`time`) and `price` (size/qty/volume optional).

Time-based bars (default 5min):
```bash
ew6 --ticks /path/to/ticks.csv --bar_type time --timeframe 5min
```

Tick-count bars (e.g., 50T):
```bash
ew6 --ticks /path/to/ticks.csv --bar_type tick --ticks_per_bar 50
```

## Spec
See `docs/PROJECT_SPEC_v1.md`.
# elliottwave
