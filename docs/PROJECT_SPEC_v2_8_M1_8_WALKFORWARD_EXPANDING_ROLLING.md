# PROJECT_SPEC v2.8 — M1.8 Walk-Forward expanding/rolling (LOCKED)

EW6 walk-forward artık 3 mod destekler:

- stability (legacy): seriyi N parçaya böl ve her parçada aynı pipeline ile performansı ölç.
- expanding: train penceresi genişler, test penceresi ileri gider (OOS).
- rolling: train penceresi sabit uzunlukta kayar, test penceresi ileri gider (OOS).

CLI:
- --walk_forward
- --wf_splits N
- --wf_min_bars N
- --wf_mode stability|expanding|rolling
- --wf_train_bars N
- --wf_test_bars N
- --wf_step_bars N

Not: EW6 şu an parametre fit etmiyor; OOS segmentlerde "aynı kural seti" ile backtest yapılır.
