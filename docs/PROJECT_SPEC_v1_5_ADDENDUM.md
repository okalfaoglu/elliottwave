# PROJECT_SPEC_v1.5_ADDENDUM (LOCKED)

Date: 2026-02-09

## M1 Stabilization + Next Improvements

Implemented in this patch:
- Stable zigzag adapter API: extract_swings / zigzag_swings returning normalized swing tuples.
- Consolidated CLI that uses the adapter and supports --auto_tune.
- Analyzer upgraded with WaveOptions + beam-budget + max_gap candidate generation.

V2 remains unchanged (Nasdaq ITCH/ITTO).
