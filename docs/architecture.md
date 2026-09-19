# ZeroMind — architecture (v0.1)

**Status:** Proposed · **Date:** 2026-09-20 · **Supersedes:** the starter [ARCHITECTURE.md](../ARCHITECTURE.md) (kept for history)

ZeroMind is a personal portfolio-intelligence system for Zerodha: a dashboard that explains everything about your
stocks and mutual funds, a paper/strategy lab to validate your own rules, and heavily guarded, human-approved
execution for real orders. Built on Kite MCP for brokerage data and execution.

**Design principle (unchanged, now structural):** agents reason and propose; a human approves; deterministic code
executes. No agent, chain, or tool call can place a live order, and the read plane contains no code that can.

## The three planes

```
             ┌────────────────────── READ PLANE (phone read-only access possible later) ─────────────────────┐
 Kite MCP ─► kite-readonly-proxy ─┐
 AMFI / mfapi ────────────────────┤                                                         React dashboard
 Screener seed / imports ─────────┼─► DATA SPINE ─► metrics ─► detectors ─► ranker ─► LLM narrator ─► (read-only)
 announcements-mcp (NSE/BSE) ─────┘  (SQLite,       (pure)     (by sleeve   Findings   + verified      Today · Portfolio
 Console CSV / CAS import            provenance)                / profile)              citations      Stock / Fund cards · Chat
                                      │ daily snapshots                          │                        │
                                      ▼                                          ▼                        ▼
                             papertrade (standalone pkg)   ◄── signal ledger   Qdrant RAG             Langfuse
                             spec ─► backtest ─► freeze ─► forward paper
                                      │ passes hard gates only
                                      ▼
             └────────────────── draft proposal (data only, never an order) ──────────────────────────────┘
                                      │
             ┌───────────── EXECUTION PLANE (separate process, 127.0.0.1 only) ──────────────────────────┐
             │ proposal store ─► policy engine ─► approval UI (+TOTP, cool-off) ─► executor              │
             │ ─► Kite MCP write tools (only holder) ─► reconcile ─► hash-chained audit log              │
             │ modes: OFF / PAPER / READ_ONLY / LIVE — LIVE disarmed by default, auto-disarms daily      │
             └────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Role | Decision |
|---|---|---|
| `zeromind-read` (FastAPI) | Data spine, analytics, nudge pipeline, LLM narrator/analyst/chat, dashboard API, job runner (daily after close + event triggers, catch-up on startup) | [0001](adr/0001-system-architecture.md), [0004](adr/0004-data-spine-and-provenance.md), [0005](adr/0005-llm-roles-and-citation-policy.md) |
| `kite-readonly-proxy` | MCP allowlist proxy exposing only `get_*` tools to everything except the executor | [0002](adr/0002-execution-safety.md) |
| `zeromind-executor` | Proposals, policy engine, approval UI (server-rendered), TOTP, arming, execution, reconcile, audit. Only holder of write tools. Localhost only | [0002](adr/0002-execution-safety.md) |
| `announcements-mcp` | Own NSE/BSE announcements service (retries, per-exchange circuit breaker, staleness flag) | [0004](adr/0004-data-spine-and-provenance.md) |
| `papertrade` | Standalone backtest + forward paper engine, declarative specs, promotion gates. No imports from ZeroMind | [0003](adr/0003-paper-strategy-lab.md) |
| `web/` (React, Vite, TS) | Rich read-only dashboard + strategy rule builder | [0001](adr/0001-system-architecture.md) |

**Stack:** Python 3.11+, FastAPI/Uvicorn, LangGraph (selective), LiteLLM, FinBERT (`transformers`), local `sentence-transformers`,
Qdrant, SQLite, Langfuse, `httpx`/`tenacity`, Pytest + `pytest-asyncio` + `respx`, Docker Compose, GitHub Actions.

**Proposed monorepo layout (not yet created):**

```
packages/{papertrade, zeromind, zeromind_executor, announcements_mcp}/
web/            docs/{architecture.md, adr/}      docker-compose.yml      .github/workflows/
```

## Scope

- **v1 instruments:** delivery equity and mutual funds (Zerodha only). Instrument kinds are extensible (ETFs, gold, bonds later).
- **Out of scope, enforced in code:** F&O and any non-delivery product type (rejected by the execution policy engine).
- **Mutual-fund actions in v1:** recommendation cards; the user executes in Coin (no MF order tools in the Kite MCP surface seen so far — to be verified).
- **Investment style is a UI setting** (sleeves with per-sleeve profile; user assignment first, then inference).

## Phasing

| Phase | Contents |
|---|---|
| **P0 Foundations** | Skeleton + CI; ports/interfaces; spine schema; **verify Kite historical data and MCP shapes**; read-only proxy; Console CSV + CAS importers; daily snapshot job |
| **P1 Read-only dashboard** | Today + Portfolio; per-stock and per-fund cards; sleeves; profile/policy statement; fundamentals seed; AMFI ingestion; announcements service; metrics → detectors → ranker → cited narrator; chat Q&A; signal ledger. **No execution** |
| **P2 Paper lab v1** | `papertrade` package; spec + UI builder; backtest + forward runs; Nifty 100; validity gates; reports |
| **P3 Guarded execution** | Executor, policy engine, approval UI, TOTP, arming, audit, reconcile. **PAPER mode first**, then LIVE with tiny caps |
| **V2 (noted, deferred)** | MF look-through overlap; alternatives (peer/category comparison with switching cost); forward-looking (goal projection, Monte Carlo, stress); MF lab rules (SIP step-up, rebalance-on-drift, value averaging); holdings/watchlist universe; read-only phone access via private mesh; ETFs/gold/bonds; GTT with expiry; point-in-time universe; OpenTelemetry on custom MCP servers; OAuth 2.1 on `announcements-mcp` if exposed beyond localhost; external assets via statement import |

Phases follow risk, not features: nothing that touches real money exists until three phases of read-only value are built.

## Deviations from the starter ARCHITECTURE.md

1. Execution is a separate process; everything else uses a read-only proxy (starter: one graph with write tools present).
2. `place_gtt_order` excluded from v1.
3. Nudge/analytics pipeline is deterministic; the four agents reduce to a research-brief workflow, chat Q&A, and the executor workflow.
4. A rich **read-only** dashboard was added (starter: minimal approval UI only); the approval UI stays minimal.
5. New: paper lab, sleeves, provenance spine, signal ledger, mandatory verified citations.
6. Starter open decisions resolved: embeddings → local `sentence-transformers`; gate delivery → server-rendered localhost page with TOTP; fundamentals → manual seed first.

## Open verification items (P0)

- Does the user's Kite plan / MCP return usable historical candles, and with what limits? Are they adjusted for corporate actions?
- Exact Kite MCP write/MF tool surface and response shapes (holdings, MF holdings).
- Langfuse hosting: Cloud for development vs self-host (v3 needs Postgres, ClickHouse, Redis, object storage).
- Signal ledger scope (proposed, not yet confirmed).

## Known risks

NSE/BSE scraping ToS and brittleness · FinBERT trained on news, not filings · Kite daily session expiry · survivorship bias in the v1
lab universe · personal-use tool, not investment advice (SEBI considerations if ever shared).

## Decision index

| ADR | Topic |
|---|---|
| [0001](adr/0001-system-architecture.md) | Three planes, two processes, selective LangGraph, stack |
| [0002](adr/0002-execution-safety.md) | Layered guardrails for real-money orders |
| [0003](adr/0003-paper-strategy-lab.md) | Standalone paper & strategy lab |
| [0004](adr/0004-data-spine-and-provenance.md) | Provenance spine, ingestion, sleeves |
| [0005](adr/0005-llm-roles-and-citation-policy.md) | LLM roles, nudge pipeline, verified citations |

## Revision history

- **v0.1 (2026-09-20)** — initial version from the design review; to be refined in later sub-versions from feedback.
