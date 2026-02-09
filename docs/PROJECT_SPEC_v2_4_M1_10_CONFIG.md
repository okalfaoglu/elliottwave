# PROJECT_SPEC v2.4 — M1.10 Config (LOCKED)

Amaç:
- Parametreleri tek yerde yönetmek (CLI + file + env)
- Defaultlar + override mekanizması
- Config provider interface (V2: DB)

M1:
- TOML/JSON config file
- Env prefix `EW6_` ve `__` nesting (örn. EW6_EXCHANGE__BINANCE__TIMEOUT_S=15)

V2:
- DB-backed dynamic config provider
- Secrets management integration
