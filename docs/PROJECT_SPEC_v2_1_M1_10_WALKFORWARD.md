# PROJECT_SPEC v2.1 — M1.10 Walk-forward (LOCKED)

Tarih: 2026-02-09

## Amaç
Batch sonuçlarının “tek dönem şansı” olmasını azaltmak için, bar datasını N parçaya bölüp aynı pipeline'ı her parçada çalıştırarak stabilite ölçmek.

## Eklenenler
- `ew6.run.walkforward.walk_forward_metrics`
- CLI flag'leri:
  - `--walk_forward`
  - `--wf_splits` (default 3)
  - `--wf_min_bars` (default 200)
- Batch report alanları:
  - `wf_splits`, `wf_pos_frac`, `wf_ret_mean`, `wf_ret_std`, `wf_mdd_mean`, `wf_trades_mean`, `wf_score`
- Ranker stabilite sinyalini skora ekler.

## Limitler
- Bu “tam” walk-forward değil; hızlı bir robustness check.
- Funding/fee modelleri ve OOS/IS ayrımı V2'de genişletilecek.
