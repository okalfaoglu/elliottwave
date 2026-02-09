# PROJECT_SPEC_v1.6_ADDENDUM (LOCKED)

Date: 2026-02-09

## M1: Data Fetch Determinism + Observability (Implemented)

- Binance trades backfill now paginates backward by `endTime` (more stable than fromId flows).
- Connector exposes `last_meta` (records/pages/cap_reason/earliest/latest) without changing return types.
- CLI prints trade fetch meta summary when using `--binance_data trades`.
- Added `--print_meta` to dump full fetch meta JSON to stderr.

This enables reliable debugging before adding heavier backtest + execution layers.
