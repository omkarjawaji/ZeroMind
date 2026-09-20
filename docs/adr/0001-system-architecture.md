# ADR-0001: System architecture — three planes, two processes

**Status:** Proposed (v0.1)
**Date:** 2026-09-20
**Deciders:** Omkar Jawaji

## Context

ZeroMind started as a multi-agent trading-signal system (see the starter
[ARCHITECTURE.md](../../ARCHITECTURE.md)). Through design review it grew into a product with three
distinct jobs that carry very different risk:

| Plane | Job | Risk |
|---|---|---|
| **A. Portfolio Intelligence** | Read-only briefing on the whole portfolio, each stock and each mutual fund | None |
| **B. Strategy & Paper Lab** | Test the user's own technical rules on dummy capital | None (simulated) |
| **C. Guarded Execution** | Real buy/sell orders on Zerodha | Real money |

Forces at play:

- Real-money actions need defence in depth; LLMs and prompts are advisory, not enforceable.
- The Kite access token is all-powerful (no read-only token), so any process holding it can trade.
- Most of the value (metrics, allocation, risk, overlap) is deterministic; LLMs add value on unstructured text and explanation.
- It is a single-user tool, but also a portfolio project for agentic-AI engineering, so LLM use should be deliberate.
- The paper lab should be reusable in a separate future project.
- Scope v1: Zerodha only; delivery equity and mutual funds; no F&O.

## Decision

1. **Split the system into a read plane and an execution plane, as separate processes.**
   - `zeromind-read` (FastAPI): data spine, analytics, nudge pipeline, LLM narrator/analyst/chat, dashboard API, job runner.
   - `zeromind-executor` (separate process, bound to `127.0.0.1`): proposals, policy engine, approval UI, execution, audit. The **only** holder of Kite write tools.
   - Everything except the executor reaches Kite through a **read-only allowlist proxy** (`kite-readonly-proxy`).
2. **Ship the paper lab as a standalone package** (`papertrade`) with no imports from the rest of ZeroMind. See [ADR-0003](0003-paper-strategy-lab.md).
3. **Use LangGraph selectively**, only where checkpoint/interrupt or multi-step retrieval earn their keep:
   - the research-brief workflow (retrieve → read → score sentiment → synthesize), and
   - the propose → approve → execute workflow.
   The nudge/analytics pipeline is a **deterministic scheduled batch**, not an agent loop. See [ADR-0005](0005-llm-roles-and-citation-policy.md).
4. **Access Kite through Kite MCP behind ports** (`BrokerReadPort`, `BrokerExecutionPort`) so the transport can change without touching callers.
5. **Frontend:** a rich **read-only** React (Vite + TypeScript) SPA for the dashboard; a deliberately minimal **server-rendered** approval page inside the executor.
6. **Stack:** Python 3.11+, FastAPI/Uvicorn, LiteLLM (model gateway), FinBERT via `transformers`, Qdrant (RAG), SQLite (v1 storage), Langfuse (tracing), `httpx` + `tenacity` + circuit breaker for the announcements service, Pytest + `respx`, Docker Compose, GitHub Actions.
7. **Embeddings:** local `sentence-transformers` (self-hostable, no per-call cost, matches local FinBERT).

## Options Considered

### Option A: LangGraph, used selectively (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | Medium: one dependency, used in two places |
| Cost | Low (open source) |
| Scalability | Ample for a single-user tool |
| Team familiarity | Already in the starter design; strong fit for the portfolio goal |

**Pros:** built-in checkpointing and `interrupt` for the approval workflow; graph state is inspectable; good tracing hooks.
**Cons:** framework coupling; safety checks must not depend on its semantics (mitigated: safety-critical checks are plain functions re-run at the executor boundary).

### Option B: Claude Agent SDK

| Dimension | Assessment |
|---|---|
| Complexity | Medium: HITL and durable state must be hand-built |
| Cost | Low |
| Scalability | Ample |
| Team familiarity | Good, but less direct match for interrupt/resume |

**Pros:** Anthropic-native tool use.
**Cons:** no built-in durable interrupt/checkpoint; ties orchestration to one provider despite the LiteLLM gateway goal.

### Option C: Plain Python state machine

| Dimension | Assessment |
|---|---|
| Complexity | Low to start, grows with features |
| Cost | Low |
| Scalability | Ample |
| Team familiarity | High |

**Pros:** maximum control, no framework risk. **Cons:** re-implements checkpointing, resume and tracing; weaker portfolio signal for an agentic-AI role.

### Option D (rejected): single process, single graph (the starter design)

Simple, but every agent shares a process with the write tools. A prompt-injected announcement or a bug then sits one tool call away from a live order. Rejected in favour of capability isolation.

## Trade-off Analysis

- **Two processes vs one:** more operational surface (two services, two databases, an IPC contract) in exchange for a boundary that cannot be crossed by an LLM. Worth it because the cost of a wrong live order is unbounded and the added surface is small.
- **Selective LangGraph vs graph-everything:** fewer "agents" than the starter, but each remaining use is justified, and deterministic code is unit-testable without model calls.
- **React SPA + server-rendered approval page:** two UI technologies, but the only page that can approve a trade has almost no third-party frontend code.
- **SQLite:** trivial to run and back up; revisit if the read plane needs concurrent writers or the executor moves off the local machine.

## Consequences

- **Easier:** reasoning about safety (the read plane has no execute code path); testing (pure metrics and detectors); reusing the lab.
- **Harder:** two deployables to run and version; a defined contract between planes (draft-proposal data only).
- **To revisit:** Langfuse self-hosting (v3 needs Postgres, ClickHouse, Redis and object storage; consider Langfuse Cloud for development); moving off SQLite; whether a second broker is ever needed (currently a non-goal).

## Action Items

1. [ ] P0: create monorepo skeleton `apps/{zeromind,zeromind_executor,papertrade,announcements_mcp,kite_readonly_proxy}`, `web/`, CI.
2. [ ] P0: define ports/interfaces: `BrokerReadPort`, `BrokerExecutionPort`, `MarketDataProvider`, `FundamentalsProvider`, `MFDataProvider`, `AnnouncementsProvider`, `TransactionHistoryImporter`, `ApprovalChannel`.
3. [ ] P0: build `kite-readonly-proxy` with an allowlist of `get_*` tools; contract-test that write tools are unreachable through it.
4. [ ] P0: decide Langfuse hosting (Cloud for dev vs Compose).
5. [ ] P1–P3: follow the phasing in [architecture.md](../architecture.md).
