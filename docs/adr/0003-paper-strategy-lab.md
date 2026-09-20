# ADR-0003: Paper & strategy lab — a standalone, bias-aware sandbox

**Status:** Proposed (v0.1)
**Date:** 2026-09-20
**Deciders:** Omkar Jawaji

## Context

The user wants to paper-trade an allocated dummy capital against their own technical-analysis metrics and
triggers, to validate rules, build trust in the system's signals, learn, and track decision quality. The sandbox
must be **modular** so it can seed a separate project later.

Assessment of the idea (from design review):

- **Valuable** as one stage of a validation pipeline: *define rules → backtest → freeze → forward paper → (small live)*.
- **Weak** as a standalone discovery tool: a few weeks of forward daily signals yield a handful of trades, so luck dominates; tuning against watched results overfits; naive fills at last price ignore slippage and charges; paper trading does not test discipline under real loss.
- **Technical triggers on mutual funds are weak** (single daily NAV, no volume). MF value in the lab is allocation/SIP/rebalance rules, deferred to a later phase.

## Decision

Build the lab as a **standalone Python package `papertrade`** with its own CLI and tests, **no imports from ZeroMind**.
ZeroMind depends on it via adapters; never the reverse.

1. **One engine, two clocks.** Backtest (simulated clock replaying history) and forward paper (real clock, daily after close) share the same strategy, fill and ledger code.
2. **Ports:** `MarketDataPort`, `Strategy`, `FillModel`, `Ledger`, `Clock`.
3. **Rules are a declarative spec** (YAML/JSON) — canonical, versioned, hashable. A no-code UI builder in the dashboard emits it; power users can edit the spec. No Python plugins in v1.
4. **Freeze by hash.** Forward paper only runs frozen spec hashes. Editing a spec yields a new hash and **restarts its forward clock**. An experiment ledger records every variant tried.
5. **Scope v1:** daily bars, delivery only, stocks. Universe = **broad index (Nifty 100)** as a tagged union (`{type: index}` now; `{type: list}` for holdings/watchlist in v2).
6. **One virtual account and ledger per strategy**, each with its own dummy capital, so strategies can be compared side by side.
7. **Hard promotion gates.** The "validated" badge, and the ability to emit **draft proposals**, require all of: minimum trade count; out-of-sample (walk-forward) pass; beats the random-entry baseline after costs; minimum forward-paper duration. Thresholds are config, set when P2 starts. The lab has **no code path to order placement**; a validated strategy can only emit draft-proposal data that enters the normal human gate ([ADR-0002](0002-execution-safety.md)).

**Illustrative spec (values are examples, not recommendations):**

```yaml
name: trend-pullback
version: 1
universe: { type: index, name: NIFTY_100 }
timeframe: 1d
capital: 200000
entry:
  all:
    - { indicator: sma, period: 50,  op: ">", ref: { indicator: sma, period: 200 } }
    - { indicator: rsi, period: 14,  op: "<", value: 35 }
exit:
  any:
    - { indicator: rsi, period: 14, op: ">", value: 65 }
    - { stop: { type: atr, multiple: 2.5 } }
    - { max_holding_days: 60 }
sizing: { type: fixed_fraction, fraction: 0.10 }
limits: { max_positions: 8 }
fills: { entry: next_open, slippage: liquidity_scaled }
```

**Bias and realism controls built into the engine:**

| Concern | Control |
|---|---|
| Lookahead | Signal on day *t* close fills at day *t+1* open; indicators only see data ≤ *t* |
| Survivorship | v1 reports labelled "survivorship-biased (current constituents)"; forward-paper stage is bias-free; v2 option: point-in-time liquidity-based universe from bhavcopy (needs corporate-action adjustment) |
| Costs | Liquidity-scaled slippage; dated charge schedule in config (brokerage, STT, stamp duty, exchange/SEBI fees, DP charges) since rates change |
| Small samples | Warn when trade count is too low to be meaningful |
| Multiple testing | Count variants tried; warn that the best of many is often luck |
| Baselines | Compare to benchmark and to random entries with the same exposure and holding periods |
| Live drift | Forward results compared with the backtest's expected distribution |

**Reported metrics (initial set):** CAGR, max drawdown, Sharpe/Sortino, hit rate, expectancy, turnover, cost drag, exposure, and outcome vs benchmark and baseline.

## Options Considered

### Option A: Standalone package with declarative specs (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | Medium |
| Cost | Low |
| Scalability | Ample (daily bars, ~100 symbols) |
| Team familiarity | Medium |

**Pros:** reusable; freezable by hash; testable; safe to run. **Cons:** spec language limits expressiveness; must maintain an indicator set.

### Option B: Lab embedded inside ZeroMind

Lower up-front friction but couples lab code to the data spine and dashboard, defeating reuse. Rejected.

### Option C: Python-plugin strategies

| Dimension | Assessment |
|---|---|
| Complexity | Medium–High |
| Cost | Low |
| Scalability | Ample |
| Team familiarity | High |

**Pros:** unlimited expressiveness. **Cons:** cannot be hashed meaningfully, so "freeze" is unenforceable; arbitrary-code security surface. Possible later escape hatch inside the standalone package only.

### Option D: Forward paper trading only (no backtest)

Slow and statistically weak (see Context). Rejected as the sole mode.

## Trade-off Analysis

Rigour costs speed: gates and warnings will often say "not proven". That is intended. A lab that flatters the user's
rules is worse than none, since its results feed decisions about real money. The declarative spec trades flexibility for
enforceable freezing.

## Consequences

- **Easier:** honest comparison of rules; reuse in another project; deterministic tests.
- **Harder:** broad-universe history needs bulk data and corporate-action adjustment (verify whether Kite history is adjusted; NSE bhavcopy is not).
- **To revisit:** MF allocation/SIP/rebalance rules; holdings/watchlist universe; point-in-time universe; pandas-ta/TA-Lib vs an in-house indicator set (Windows install friction for TA-Lib; check maintenance status of alternatives).

## Action Items

1. [ ] P0: verify price-history source and rate limits (Kite `get_historical_data`, NSE bhavcopy, yfinance) and adjustment for splits/bonus.
2. [ ] P2: define spec schema (versioned, JSON-Schema validated) and spec-hash function.
3. [ ] P2: implement engine, fill model, charge schedule config, ledger, clocks.
4. [ ] P2: implement walk-forward split, random-entry baseline, multiple-testing counter, gate evaluator.
5. [ ] P2: dashboard rule builder that emits the spec.
6. [ ] P2: `papertrade` CLI (`papertrade run spec.yaml`) usable standalone.
