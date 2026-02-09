# PROJECT_SPEC v2.2 — M1.7 Cache + Fee Schedule (LOCKED)

Tarih: 2026-02-09

## Amaç
- Batch koşularını hızlandırmak ve deterministik replay sağlamak için disk cache.
- Binance REST'te transient hatalara (429/5xx/internal error) retry/backoff ile daha dayanıklı olmak.
- Kullanıcıların her koşuda `--fee_bps` yazmasını önlemek için basit fee schedule helper.

## Eklenen CLI flag'leri
- `--cache_dir` (default: `.cache/ew6/binance`)
- `--cache_ttl_s` (default: `0` => expire olmaz)
- `--no_cache`
- `--retries`
- `--timeout_s`

- `--fee_model manual|schedule` (default manual)
- `--fee_side maker|taker` (default taker)

## Notlar
- Fee schedule “account-specific” değildir; sadece güvenli varsayılanlar.
- Backtest default olarak market/taker varsayımıyla gider.
