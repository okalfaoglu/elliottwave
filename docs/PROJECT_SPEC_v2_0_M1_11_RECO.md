# M1.11 Recommendations (LOCKED)

Date: 2026-02-09

Implemented:
- Ranking after batch runs using a simple weighted score combining:
  - bt_totalret, bt_mdd, bt_sharpe
  - best_conf, best_score
  - bt_trades (stability proxy)

CLI:
- `--rank_top N` (default 5)
- `--export_reco out/reco.json`

Also improved time range printing by using bar ts arrays when needed.

Planned:
- Walk-forward split and stability ranking (V2).
