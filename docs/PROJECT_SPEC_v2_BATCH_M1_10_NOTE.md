# M1.10 NOTE (LOCKED)

Date: 2026-02-09

## Batch / Multi-run

Implemented in M1.8:
- `--symbols` and `--timeframes` comma-separated lists.
- Aggregated report export:
  - `--export_report report.json`
  - `--export_report_csv report.csv`

Planned next:
- Venue-specific fee schedules (spot vs futures; maker/taker).
- Funding rate / rollover models (V2 milestone).
- Parallel execution with rate limiting per venue.
