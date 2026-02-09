# PROJECT_SPEC_v1.8_ADDENDUM (LOCKED)

Date: 2026-02-09

## M1: Backtest Summary + Trade Export (Implemented)

- Added `ew6.backtest.simple`:
  - pattern -> 1 trade mapping
  - equity curve, total return, max drawdown, winrate
- CLI flags:
  - `--backtest`
  - `--initial_cash`, `--risk_fraction`, `--min_confidence`
  - `--export_trades path.csv`

Note: This is a *minimal* deterministic backtest. Execution/slippage/fees and
bar-level entries/exits are planned for later milestones.
