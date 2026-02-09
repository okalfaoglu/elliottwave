# PROJECT_SPEC v2.7 — Notifications (Telegram/Email) (LOCKED)

M1 kapsamı:
- Telegram Bot API
- SMTP Email

Mesaj formatı:
- compact (default): kısa tek-iki satır özet
- pretty: çok satırlı okunur rapor
  - Telegram için opsiyonel: `--notify_markdown` (basit **bold**)

Env:
- EW6_NOTIFY_CHANNELS
- EW6_NOTIFY_FORMAT
