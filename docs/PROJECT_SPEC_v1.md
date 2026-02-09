# EW6 Project Specification (v1.0 — LOCKED)

**Status:** Locked baseline spec. Changes must be done via versioned addenda (v1.1, v1.2, ...).

## 0. Goal
Build a robust, production-grade Elliott Wave analysis and trading research stack that supports:
- tick ingestion (optional) and resampling to bars
- swing extraction (zigzag/fractals/ATR)
- Elliott Wave candidate generation + rule-based validation
- pattern scoring + confidence calibration
- signal generation (entry/exit, TP/SL)
- event-driven backtesting with costs + walk-forward evaluation
- optional live execution connectors
- visualization and notebook-based research

**Non-goals (v1):**
- fully automated portfolio management across many symbols
- HFT/tick-by-tick execution (we resample to bars)

## 1. Core Principles
1. **Standard data models**: every module speaks the same dataclasses.
2. **Deterministic core**: EW detection is rule-based and testable.
3. **Separation of concerns**: data → swings → patterns → signals → execution.
4. **Performance control**: candidate explosion is bounded (pruning + budgets).
5. **Reproducible evaluation**: walk-forward backtesting and cost modeling.

## 2. Repository Layout
See `src/ew6/...` and keep these boundaries:

- `data/`: ingestion and bar building
- `swing/`: extrema extraction / de-noising
- `ew/`: wave detection core and detector adapters
- `features/`: indicators and microstructure approximations
- `signals/`: mapping patterns to trades
- `backtest/`: event-driven simulator + metrics + walk-forward
- `trading/`: execution + risk management
- `viz/`: plotting utilities
- `ml/`: optional models (RL/predictors) built on top of pattern features
- `notebooks/`: research (calls library; no core logic lives only in notebooks)

## 3. Standard Data Models (MUST)
### 3.1 Bars
- `Bar`: single OHLCV
- `BarSeries`: DataFrame wrapper with validation

### 3.2 Swings
- `SwingPoint`: index, timestamp, price, type(high/low)

### 3.3 Waves
- `WavePoint`: idx + price
- `WavePattern`: normalized container
  - `pattern_type`: impulse_12345, correction_abc
  - `points`: ordered turning points
  - `score`: numeric ranking
  - `meta`: detector-specific details

### 3.4 Signals/Trades
- `Signal`: side(buy/sell/flat), confidence, reason, optional pattern
- Backtest uses a normalized `Trade` record (dict for v0.1, dataclass from v1.1)

## 4. Pipeline (Happy Path)
1. (optional) tick ingestion → `data/bar_builder.resample_to_bars()`
2. `swing/zigzag.py` (v1.0) to generate swing points
3. `ew/detectors/analyzer.scan_impulses_from_swings()`
4. `ew/core/scorer` ranks candidates (v1.1)
5. `signals/generator.generate_signals()` generates entry/exit intent
6. `backtest/engine` simulates execution with costs (v1.1+)
7. `viz/plot_waves` can render the selected pattern (v1.1)

## 5. Elliott Wave Detection (Design)
### 5.1 Primary Detector (P5-derived)
Port the following concepts:
- MonoWave construction
- WaveOptions (skip/noise tolerance)
- WaveRules validation (impulse and correction)
- Numba-accelerated primitives

### 5.2 Secondary Detector (P3-derived)
Use `taew`-style fib checks as:
- alternative detector for cross-validation
- sanity check scoring boost when both detectors agree

### 5.3 Candidate Explosion Control (MANDATORY)
Implement pruning in this order:
1. Swing prefilter (zigzag threshold and/or ATR-based threshold)
2. Max patterns per start (budget)
3. Early fail-fast rules
4. Beam search: keep top-K partial candidates
5. Timeframe cascade: coarse timeframe generates candidates, finer refines

## 6. Scoring & Confidence
Scoring combines:
- rule satisfaction margin (how far from thresholds)
- fib alignment quality
- trend consistency
- cross-detector agreement
- volatility regime normalization

Confidence calibration:
- isotonic or logistic calibration from walk-forward backtests (v1.2)

## 7. Backtesting (Evaluation Standard)
### 7.1 Engine
Event-driven simulation on bar close.

### 7.2 Costs
At minimum:
- maker/taker fee
- spread approximation
- slippage as function of volatility/volume (configurable)

### 7.3 Validation
Walk-forward:
- Train/fit params (if any) on window A
- Test on next window B
- Roll forward

## 8. Live Trading (Optional)
Execution must be isolated:
- strategy produces orders
- executor sends orders to broker
- risk manager can veto

## 9. Testing Requirements
- unit tests for swing extraction
- unit tests for fib checks and rule validators
- regression tests for sample patterns
- performance tests for candidate scan budgets

## 10. Milestones
### M0 (DONE in scaffold)
- package skeleton, minimal end-to-end pipeline works

### M1
- replace naive detector with P5 port (MonoWave + Rules)
- add pruner/budget system
- add basic scorer

### M2
- add cost model + event-driven backtest
- add walk-forward harness

### M3
- add visualization utilities
- add taew adapter + agreement scoring

### M4 (Optional)
- RL/predictor layer using pattern features


## 11. Work Breakdown (File-by-File)

### 11.1 `ew6/data/`
- `types.py` (v1.0): keep stable. Add:
  - `to_numpy()` helpers (close/high/low arrays)
  - strict dtype checks (float64)
- `bar_builder.py` (v1.0):
  - support `trade` and `quote` tick schemas via adapters
  - allow timezone normalization to UTC
  - add unit tests with synthetic tick streams
- `sources/` (v1.1):
  - `csv_source.py`: load OHLCV
  - `parquet_source.py`: load bars/ticks
  - `binance_source.py` (optional): fetch klines or stream

### 11.2 `ew6/swing/`
- `zigzag.py` (v1.0): replace with:
  - ATR-based zigzag threshold option
  - strict alternation high/low enforcement
  - ability to emit last unconfirmed swing (optional)
- `fractals.py` (v1.2): Bill Williams fractals extrema
- `filters.py` (v1.1):
  - outlier removal
  - minimum bar distance between swings
  - merge micro-swings

### 11.3 `ew6/ew/core/`
- `model.py` (v1.0): keep stable.
- `functions.py` (v1.1): port/implement numba primitives:
  - local extrema scan
  - fast fib ratio calculations
  - monotonic segment checks
- `monowave.py` (v1.1): implement MonoWave builder:
  - input: swings or prices
  - output: monowave segments with direction, length, amplitude
  - skip_n logic (noise tolerance)
- `rules.py` (v1.1): implement WaveRules:
  - impulse rules (wave2 retracement bounds, wave3 extension, wave4 overlap rules, wave5 relationships)
  - correction rules (ABC: zigzag/flat/triangle later)
  - rule margin outputs (for scoring)
- `options.py` (v1.1): WaveOptions and parameter grid
- `pruner.py` (v1.1): candidate budget and beam search
- `scorer.py` (v1.1): convert rule margins + fib fit to `pattern.score`

### 11.4 `ew6/ew/detectors/`
- `analyzer.py` (v1.0): placeholder replaced in v1.1 with:
  - `scan()` that returns top-N patterns
  - time/compute budget options
  - optional multi-timeframe cascade
- `taew_adapter.py` (v1.3):
  - wrap P3-like fib checks
  - normalize output into `WavePattern`
  - agreement scoring utility

### 11.5 `ew6/features/`
- `indicators.py` (v1.2): RSI, ATR, volatility
- `microstructure.py` (v1.2): spread/slippage approximations for backtest

### 11.6 `ew6/signals/`
- `rulesets.py` (v1.2): explicit entry/exit templates
- `generator.py` (v1.0): placeholder upgraded:
  - pattern-type specific policies
  - SL/TP derived from fib levels
  - conflict resolution when multiple patterns overlap

### 11.7 `ew6/backtest/`
- `engine.py` (v1.0): toy → (v1.2) event-driven:
  - order types (market/limit)
  - partial fills (optional)
  - positions with PnL tracking
- `costs.py` (v1.2): fees+spread+slippage
- `metrics.py` (v1.2): returns, Sharpe, max drawdown, win rate
- `walkforward.py` (v1.2): rolling split evaluator

### 11.8 `ew6/trading/`
- `risk_manager.py` (v1.3):
  - max position, max daily loss, volatility guard
- `executor.py` (v1.3): simulated & live executor interface
- `portfolio.py` (v1.3): multi-position accounting (optional)

### 11.9 `ew6/viz/`
- `plot_waves.py` (v1.2):
  - plot bars + swings + wave labels
  - export to PNG

### 11.10 `ew6/ml/` (Optional)
- `predictors.py` (v1.4): feature extraction from patterns
- `rl_policy.py` (v1.4): policy on top of signals (not core)

## 12. Definition of Done (v1.0 locked)
- EW6 installs as a package
- CLI runs end-to-end on a bar CSV
- A swing extractor exists (even if simple)
- An EW detector returns at least one `WavePattern` (even if placeholder)
- Signals generated and a backtest runs

