# EW6 Progress Tracker

This file is meant to be updated frequently (not locked).  
Status legend: ✅ done | 🟡 partial | ⬜ not started

---

## M0 — Scaffold

- ✅ Python packaging / editable install
- ✅ CLI entrypoint (`ew6`)
- ✅ Minimal dependency set

---

## M1 — Offline Research Engine

### Data & Connectors
- ✅ Binance OHLCV (spot + futures)
- ✅ Binance trades (aggTrades) with backfill
- ✅ Fetch meta/observability (`last_meta`)
- ⬜ Additional venues (Bybit/OKX/Coinbase)

### Bar Building
- ✅ Time bars (default 5m)
- ✅ Tick bars (e.g., 50T)
- ⬜ Volume/Dollar bars

### Swings / ZigZag
- ✅ ZigZag adapter API (`extract_swings`)
- ✅ Normalized swing output

### Elliott Wave Detection
- ✅ Monowaves from swings
- ✅ Impulse 1–5 detector baseline
- ✅ Candidate budget / beam search
- ✅ Scoring + confidence
- ✅ NMS pruning
- ⬜ Corrective patterns (ABC etc.)
- ⬜ Multi-degree wave labeling

### Backtest / Research
- ✅ Minimal backtest summary
- ✅ Entry mode: pattern vs bar close
- ✅ Fees + slippage (bps)
- ✅ Trade export (via report CSV/JSON; per-trade CSV is optional future)
- 🟡 More realistic position management (overlap, stops/targets)

### Batch / Automation
- ✅ Multi-symbol + multi-timeframe batch
- ✅ Export report JSON/CSV
- ✅ Ranker + export recommendations
- ⬜ Walk-forward stability splits

---

## V2 — Market Data Feeds & Streaming

- ⬜ Binance WebSocket stream
- ⬜ Persistent storage & caching
- ⬜ Nasdaq ITCH/ITTO ingestion (per earlier decision: V2)
- ⬜ Execution engine / OMS / risk (only if we choose to go there)
