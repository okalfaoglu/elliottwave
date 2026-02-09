# PROJECT_SPEC v1.2 Addendum (LOCKED)

Date: 2026-02-08

## v0.5.0 (M1 continuation)
- Added MonoWave extraction layer inspired by ElliottWaveAnalyzer (P5).
- Added WaveOptions for monowave skip and scan budgets.
- Updated impulse scanning to use consecutive monowaves with conservative rules.
- Kept pruning (NMS) + confidence scoring pipeline.

## Deferred to V2
- Nasdaq ITCH (TotalView-ITCH) parsing + order book reconstruction.
- Nasdaq ITTO options feed parsing.
