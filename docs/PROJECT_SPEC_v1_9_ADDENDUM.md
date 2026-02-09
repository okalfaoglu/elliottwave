# PROJECT_SPEC_v1.9_ADDENDUM (LOCKED)

Date: 2026-02-09

## M1: Backtest Realism + Costs (Implemented)

- Backtest now supports:
  - `--entry_mode bar` to use bar close prices at leg indices
  - `--fee_bps` and `--slippage_bps` (applied on entry and exit)
- Added metrics:
  - profit factor (PF)
  - Sharpe-like (mean/std of trade returns)
- CLI time range now falls back to `bars.df` datetime index when `start_time/end_time` are None.

Next: fees by venue, funding/commission models (V1.10) and multi-asset batch runs.
