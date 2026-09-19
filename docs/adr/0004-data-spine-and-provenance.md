# ADR-0004: Data spine, provenance, and ingestion

**Status:** Proposed (v0.1)
**Date:** 2026-09-20
**Deciders:** Omkar Jawaji

## Context

The dashboard must let the user trust every number ("understand first"). Data comes from mixed-quality sources:
an official broker feed, official but awkward public files, and unofficial scrapes. Two gaps were found in review:

- **Transaction history.** Kite holdings give quantity and average price but **no purchase dates**, and MF holdings are similar. Without dated cash flows, XIRR, holding periods, and behaviour-based sleeve inference are impossible.
- **Fundamentals for Indian stocks.** No clean, free, official API. Screener.in has no official API and scraping is ToS-grey; `yfinance` is unofficial; NSE/BSE result filings are official but heavy to parse.

Also: this is a single-user personal tool (lower ToS risk than a shared product, but still brittle), and the PC is not always on.

## Decision

### 1. A provenance-tagged data spine

Every stored datum carries `source`, `as_of`, `fetched_at`, `staleness`, and `confidence`. The UI and the LLM layer read **only**
from the spine. A broken source degrades to "stale, last updated 3 days ago", never to a silently wrong number. Every number in the
UI is drillable to its source.

### 2. Provider interfaces per data kind

`MarketDataProvider`, `FundamentalsProvider`, `MFDataProvider`, `AnnouncementsProvider`, `TransactionHistoryImporter`. Sources are swappable and mockable (`respx`; no live calls in tests).

### 3. Phase-1 data map

| Need | Source | Status |
|---|---|---|
| Holdings, live prices, day change | Kite MCP via read-only proxy (`get_holdings`, `get_ltp`, `get_quotes`, `get_mf_holdings`) | Available |
| Stock price history (technicals, risk, benchmark) | Kite `get_historical_data`; fallback NSE bhavcopy / yfinance behind `MarketDataProvider` | **Unverified** — plan/rate limits unknown; verify in P0 |
| Corporate actions (splits/bonus) | NSE | Verify; Kite history may be unadjusted |
| MF NAV history, category, direct vs regular | AMFI daily NAV file (groups schemes by category) / `mfapi.in` | Free |
| MF expense ratio (TER) | AMFI TER disclosure | Free, separate feed |
| Stock fundamentals & valuation | **Manual Screener export as seed corpus**, cached with staleness flags, behind `FundamentalsProvider`; automate later | Decided |
| Announcements | Own NSE/BSE `announcements-mcp` (session-priming for NSE, header spoofing for BSE, retries, per-exchange circuit breaker, staleness flag) | Planned |
| Purchase dates / cash flows | **One-time import**: Zerodha Console tradebook CSV (equity) + CAS statement (MFs; `casparser`-style parser) | Decided |

### 4. Daily holdings snapshots

From day one the system snapshots holdings daily and **detects changes** (new buys/sells). Imports backfill history; snapshots
extend it. Trades made outside ZeroMind (e.g. in the Kite app) are detected this way and tagged `external`.

### 5. Sleeves and the investor profile

- A **sleeve** groups holdings and carries a style/horizon/risk budget and rule set (e.g. "Core MF SIPs", "Long-term stocks", "Swing experiments").
- **Assignment precedence: user choice > inferred > default.** The user assigns styles to chosen holdings first; the system infers the rest and labels each inference with its reason and confidence.
- Defaults: MFs → long-term SIP sleeve; stocks unassigned until chosen or inferred.
- Inference inputs: instrument kind, holding period and buy pattern (from imported history/snapshots), position size, volatility/market cap. Without imported history, inference confidence is low and labelled as such.
- The **investor profile / policy statement** (goals, risk tolerance, max single-stock weight, sector caps, cash buffer, tax regime) is editable in the UI, not baked into code. Investment style is a UI choice, not an architectural assumption.

### 6. Job model

Daily after-close batch **plus event triggers** (new announcement, results date, large price move). Because the PC may be off, the job runner **catches up on startup** for missed runs.

### 7. Storage

SQLite for v1 (spine, snapshots, ledgers). The executor keeps its **own** database and audit log; the read plane consumes proposal status through a read-only view. Qdrant holds text chunks for RAG.

## Options Considered

### Option A: Provenance spine + import once + snapshots (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | Medium |
| Cost | Low |
| Scalability | Ample |
| Team familiarity | Medium |

**Pros:** traceable numbers; accurate XIRR; graceful degradation. **Cons:** manual import step; parsing work for CAS/Console formats.

### Option B: Snapshots only, going forward

Simplest, but XIRR and holding-period features are missing or approximate for a long time and existing SIP history is lost. Rejected.

### Option C: Query sources on demand, no spine

No history, no provenance, slow pages, and rate-limit exposure. Rejected.

### Fundamentals source alternatives

| Option | Verdict |
|---|---|
| Manual Screener export seed (chosen) | Lowest ToS/brittleness risk, low volume needed for a personal portfolio; manual effort |
| `yfinance` | Automated but unofficial; coverage and field quality vary |
| Official NSE/BSE filings only | Most defensible but heavy XBRL parsing; slows P1 |

## Trade-off Analysis

The manual steps (Console/CAS import, Screener export) buy correctness and lower legal/brittleness risk at the price of some
user effort, mitigated by making imports one-time and idempotent. The provenance spine costs schema overhead on every table but is
what makes the "where did this come from?" promise and the LLM citation policy ([ADR-0005](0005-llm-roles-and-citation-policy.md)) possible.

## Consequences

- **Easier:** honest stale-data handling; swapping sources; citation validation (facts have stable ids and as-of dates).
- **Harder:** every ingestor must write provenance fields; import parsers need fixtures and tolerance for format changes.
- **To revisit:** automating fundamentals; MF portfolio-disclosure ingestion for look-through overlap (V2; heterogeneous per-AMC files); ETFs/gold/bonds as new instrument kinds; external assets via statement import.

## Action Items

1. [ ] P0: verify Kite MCP response shapes for holdings/MF holdings and `get_historical_data` access, limits and adjustment behaviour.
2. [ ] P0: define spine schema with provenance columns; migrations.
3. [ ] P0: implement Console tradebook and CAS importers with fixtures; idempotent re-import.
4. [ ] P0: daily snapshot job with change detection and `external` tagging; startup catch-up.
5. [ ] P1: AMFI NAV/TER ingestion; Screener export loader with staleness flags.
6. [ ] P1: `announcements-mcp` per starter design, behind `AnnouncementsProvider`.
7. [ ] P1: sleeve model, user-override-then-infer logic, profile/policy-statement UI.
