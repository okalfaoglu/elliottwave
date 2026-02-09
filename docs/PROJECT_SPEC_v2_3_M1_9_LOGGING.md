# PROJECT_SPEC v2.3 — M1.9 Logging (LOCKED)

Amaç:
- Uygulamanın tamamında tutarlı log üretimi
- Seviye kontrolü: debug/info/warning/error/critical
- JSON log opsiyonu + file output

M1 kapsamı:
- `ew6.logging.setup_logging(LogConfig(...))`
- stdlib logging üzerine ince wrapper

V2:
- structured tracing, correlation id, metrics export
