# PROJECT_SPEC_v1.7_ADDENDUM (LOCKED)

Date: 2026-02-09

## M1 Reliability Improvements

Implemented:
- CLI now normalizes bar data to a stable `BarSeries` model even if connectors return raw lists.
- Added exports:
  - `--export_bars path.csv`
  - `--export_patterns path.json`

This improves reproducibility and enables offline analysis/visualization in later milestones.
