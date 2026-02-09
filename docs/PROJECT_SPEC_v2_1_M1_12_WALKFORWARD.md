# M1.12 Walk-forward Stability (LOCKED)

Date: 2026-02-09

## What was added

- Walk-forward stability evaluation (`ew6.run.walkforward.walkforward_evaluate`)
  - Splits the lookback window into N contiguous segments (`--wf_splits`)
  - Runs the *same* pipeline per segment and measures:
    - wf_mean_ret, wf_std_ret
    - wf_mean_mdd
    - wf_pos_frac
    - wf_score (normalized 0..~1)
- Ranking now blends:
  - base score (single window)
  - wf_score (stability)

## CLI flags

- `--wf_splits N` (default 1 = disabled)
- `--wf_min_bars N` (default 200)

## Notes

This is a stability proxy, not a strict OOS walk-forward optimization.
V2 will include: true train->test walk-forward, parameter selection on train,
and validation on test (with transaction costs and funding).
