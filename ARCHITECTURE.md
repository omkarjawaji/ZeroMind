# ZeroMind — architecture & build spec

> **Superseded by [docs/architecture.md](docs/architecture.md) (v0.1).** Kept as the original starter for history.

Multi-agent portfolio intelligence system. Portfolio project for an agentic AI
engineering transition. Built on Zerodha's Kite Connect (via Kite MCP) as the
live brokerage data/execution layer.

## Design principle

Agents reason and propose. A human executes. No agent, chain, or tool call in
this system is permitted to place a live order without an explicit manual
approval step. This is a hard constraint on the architecture, not a feature
to bolt on later — the LangGraph graph must have an interrupt/checkpoint
before any node that can call `place_order` or `place_gtt_order`.

## Architecture

```
┌─────────────┐   ┌──────────────────────┐   ┌─────────────────────┐
│  Kite MCP   │   │  Announcements svc   │   │ Fundamentals corpus │
│ Portfolio,  │   │  (own NSE/BSE impl,  │   │ Screener.in, annual │
│ quotes,     │   │  not the unofficial  │   │ reports, transcripts│
│ orders      │   │  nse-bse-api lib)    │   │                     │
└──────┬──────┘   └──────────┬───────────┘   └──────────┬──────────┘
       │                     │                           │
       │                     ▼                           ▼
       │              ┌────────────────────────────────────────┐
       │              │     Embedding pipeline → Qdrant         │
       │              └──────────────────┬───────────────────────┘
       ▼                                 │
┌──────────────────────────────────────────────────────────────────┐
│                    LangGraph orchestrator                        │
│  ┌────────────────────┐        ┌─────────────────────┐           │
│  │  Portfolio agent    │        │  RAG agent           │          │
│  │  reads Kite holdings│        │  retrieves from Qdrant│         │
│  └────────────────────┘        └─────────────────────┘           │
│  ┌────────────────────┐        ┌─────────────────────┐           │
│  │  Sentiment agent    │        │  Signal synthesis    │          │
│  │  FinBERT on announcs│        │  builds trade proposal│        │
│  └────────────────────┘        └─────────────────────┘           │
└───────────────────────────────┬──────────────────────────────────┘
                                 ▼
                     ┌───────────────────────┐
                     │  Human approval gate   │   ← hard interrupt,
                     │  approve / reject      │     no auto-bypass
                     └───────────┬───────────┘
                                 ▼
                     ┌───────────────────────┐
                     │  Kite MCP execution    │
                     │  place_order (human-   │
                     │  approved only)        │
                     └───────────────────────┘
```

Cross-cutting, not part of the trade flow itself:
- **LiteLLM** — unified LLM gateway in front of all four agents; swap models
  without touching agent code.
- **Langfuse** — traces every agent call and tool invocation.

## Components

### 1. Data layer
- **Kite MCP** — portfolio (`get_holdings`, `get_mf_holdings`), market data
  (`get_quotes`, `get_ltp`, `get_ohlc`, `get_historical_data`), and execution
  (`place_order`, `place_gtt_order`, `modify_order`, `cancel_order`). Already
  validated live against the account this project targets.
- **Announcements service** — own implementation, inspired by (not copied
  from) the `bshada/nse-bse-api` approach:
  - NSE: session-priming (visit homepage, capture cookies, reuse cookie jar,
    re-prime on 403) via `httpx`.
  - BSE: header spoofing (realistic `User-Agent`/`Origin`/`Referer`), no
    cookie dance needed.
  - Wrapped behind an `AnnouncementsProvider` interface so NSE/BSE are
    swappable implementations, not hardcoded into the sentiment agent.
  - Resilience: `tenacity` retries, a circuit breaker per exchange, a
    staleness flag on every returned batch, self-imposed rate limiting.
  - Ships as its own small MCP server (`announcements-mcp`) exposing
    `get_corporate_announcements(symbol, from_date, to_date, source="auto")`.
- **Fundamentals corpus** — Screener.in data, annual reports, earnings call
  transcripts. Feeds the RAG embedding pipeline.

### 2. RAG
- Embedding pipeline chunks fundamentals/reports/announcements and writes to
  **Qdrant**.
- RAG agent retrieves relevant context at query time.

### 3. Agent layer (LangGraph)
Four agents, one orchestrator graph:
- **Portfolio agent** — current holdings, positions, margins via Kite MCP.
- **RAG agent** — retrieves fundamentals/announcement context from Qdrant.
- **Sentiment agent** — FinBERT scoring on announcement/news text.
- **Signal synthesis agent** — combines the above into a structured trade
  proposal (symbol, side, quantity, price, rationale).

### 4. Human-in-the-loop gate
- The graph interrupts after signal synthesis and before any order call.
- Delivery mechanism (pick one): CLI prompt, a minimal FastAPI+HTMX page
  listing pending proposals, or a Slack webhook.
- Only an explicit approve action resumes the graph into the execution node.

### 5. Execution
- Kite MCP `place_order` / `place_gtt_order`, called only from the
  post-approval graph node.

### 6. Persistence
- Not in the original stack notes — added because the human-gate audit trail
  needs somewhere to live: proposal created → pending → approved/rejected →
  executed. SQLite is enough for this project; no need for Postgres unless
  there's a reason to run it as a service.

## Tech stack

**Orchestration & agents**
- Python 3.11+
- LangGraph
- LiteLLM
- FinBERT (`transformers`)

**Data layer**
- Kite Connect MCP
- `httpx` (async, cookie-jar support)
- `tenacity`
- Hand-rolled circuit breaker (or `pybreaker`)

**RAG**
- Qdrant
- Embedding model — `text-embedding-3-small` or a local `sentence-transformers`
  model for a fully self-hosted setup
- `pypdf` (or similar) for report ingestion

**Serving & infra**
- FastAPI + Uvicorn
- Docker + docker-compose (Qdrant, FastAPI, Langfuse)
- Langfuse
- SQLite (proposal/approval audit log)

**Testing & CI**
- Pytest + `pytest-asyncio`
- `respx` (mock `httpx` calls for Kite/NSE/BSE — no live calls in tests)
- GitHub Actions

## Non-goals (v1)

- No autonomous order placement under any condition.
- No multi-broker support — Zerodha/Kite only.
- No custom frontend beyond the minimal approval UI.
- No fine-tuning — prompt-based agents on top of LiteLLM-routed models only.

## Future enhancements

Deliberately deferred past v1, drawing on prior MCP engineering study/prod
experience — not blocking the first working version, but worth revisiting
once the core loop (data → agents → proposal → human gate) runs end to end.

- **Resources vs. Tools on `announcements-mcp`** — v1 exposes announcements
  as a single tool call. Worth deciding deliberately whether portfolio state
  or announcement feeds are better modeled as MCP Resources (ambient
  context) rather than Tools (explicit function calls) — this is one of the
  three core MCP primitives (Tools, Resources, Prompts) and the project
  currently only uses one of them.
- **OpenTelemetry on custom MCP servers** — Langfuse covers agent-level
  tracing, but the custom MCP servers (`announcements-mcp`, and any other
  hand-built server in this project) aren't instrumented themselves. Add
  OTel spans around tool calls, cookie-priming/re-priming events, and
  circuit-breaker state changes, matching the observability standard already
  used for production MCP work.
- **OAuth 2.1 on `announcements-mcp`** — fine to skip for pure localhost use,
  but if this server is ever exposed beyond a single machine (e.g. accessed
  from another device or shared), add a proper OAuth 2.1 flow rather than
  running it unauthenticated.

## Open decisions for the next session

- Embedding model: hosted (OpenAI) vs. local (`sentence-transformers`) —
  affects whether the project is fully self-hostable.
- Human-gate delivery: CLI vs. HTMX page vs. Slack — pick one for v1, others
  can follow.
- Fundamentals ingestion: manual seed corpus vs. a scheduled scraper — start
  manual, automate later.
