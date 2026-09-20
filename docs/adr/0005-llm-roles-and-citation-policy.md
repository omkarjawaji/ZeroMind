# ADR-0005: LLM roles, the nudge pipeline, and mandatory verified citations

**Status:** Proposed (v0.1)
**Date:** 2026-09-20
**Deciders:** Omkar Jawaji

## Context

The dashboard should produce nudges and briefings drawing on "all kinds of information, analysis, and user profile".
Most of that is computation (XIRR, drawdown, weights, rolling returns, valuation percentiles) where LLMs are unreliable and
deterministic code is testable. LLMs add value on unstructured text (announcements, transcripts) and on explanation.

Users hear that "mandatory citation reduces hallucination". That is **partly** true: it helps only when enforced
mechanically. A prompt asking for citations yields fabricated or non-supporting citations. The benefit comes from verification.

## Decision

### 1. LLM roles

**Allowed:** (a) *narrator* — explains deterministic findings; (b) *announcement/transcript reader* — summarizes and scores
unstructured text into qualitative findings that cite source text; (c) *chat Q&A* over the portfolio.

**Not allowed:** computing metrics, setting thresholds, sizing positions, generating orders, or suggesting new stocks/funds to research.

LLM calls go through LiteLLM; every call and tool invocation is traced in Langfuse.

### 2. The nudge pipeline (deterministic batch)

```
Data spine ─► 1. Metrics (pure, tested)  ─► 2. Detectors (rules parameterised by sleeve/profile)
                                              │
                                              ▼
              Finding { type, severity, evidence[], rule_id, sleeve, as_of, confidence }
                                              │
                                              ▼
                        3. Ranker: severity × profile relevance × novelty; dedupe, cooldown, snooze
                                              │
                                              ▼
                        4. Narrator (LLM) + citation validator
Side channel: 5. Analyst (LLM + RAG) ─► qualitative findings that cite source text, lower confidence
```

Runs **daily after market close plus event triggers**. Not an agent loop, and unit-testable without model calls.

### 3. Nudge ladder

| Level | Meaning | Can it lead to an action? |
|---|---|---|
| **Inform** | A fact worth knowing | No |
| **Review** | Look at this holding/fund | No |
| **Consider** | A possible action, with evidence and the rule that triggered it | Stock: may create a **draft proposal** that enters the human gate ([ADR-0002](0002-execution-safety.md)). Mutual fund: recommendation card only. |

Nudges never read as a bare "buy X"/"sell Y" command; each shows its evidence, the profile rule behind it, and snooze/dismiss.

### 4. Mandatory, mechanically verified citations

Every LLM output is **structured**: a list of claims, each with citation ids.

```json
{
  "claims": [
    { "text": "Fund X has trailed its category median over rolling 3 years.",
      "cites": [ { "kind": "fact", "id": "rolling_return_3y:fund_x@2026-09-19" },
                 { "kind": "fact", "id": "category_median_3y:large_cap@2026-09-19" } ] },
    { "text": "Management flagged a delay in the plant commissioning.",
      "cites": [ { "kind": "doc", "id": "ann:NSE:20260918:4471#c3", "span": "commissioning is now expected in" } ] }
  ],
  "insufficient_evidence": false
}
```

**Validator (runs before anything is shown):**

1. Every cited id exists in the evidence set supplied for *this* request.
2. For `doc` citations, the quoted `span` appears **verbatim** in the source chunk.
3. Every number in a claim matches the cited fact(s), with unit/rounding tolerance.
4. Claims that fail are **dropped or regenerated**; if nothing survives, output the "insufficient evidence" state.
5. (Optional, later) A second lightweight pass checks that the cited text actually *entails* the claim.

The UI renders each citation as a link to the source text/metric and its as-of date. Prompt-injection text inside an announcement
is treated as data: the LLM has no tools that can act, and its output can only be claims with citations.

### 5. Signal ledger (proposed, to confirm)

Log each nudge with a timestamp and a price snapshot; measure outcomes at 1, 3 and 6 months versus benchmark. This serves "build
trust in the system's signals" and "track my own decision quality", and feeds the paper lab ([ADR-0003](0003-paper-strategy-lab.md)).

## Options Considered

### Option A: Deterministic pipeline + narrated by LLM with verified citations (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | Medium |
| Cost | Low–Medium (LLM used for text only) |
| Scalability | Ample |
| Team familiarity | Medium |

**Pros:** testable, grounded, explainable; prompt changes affect wording, not whether a nudge fires. **Cons:** validator and evidence plumbing to build; some fluent-but-unverifiable outputs are rejected.

### Option B: LLM agents decide nudges end-to-end

| Dimension | Assessment |
|---|---|
| Complexity | Medium |
| Cost | Higher (many calls) |
| Scalability | Ample |
| Team familiarity | Medium |

**Pros:** fastest to a demo. **Cons:** untestable thresholds, non-reproducible results, hallucination risk on numbers. Rejected.

### Option C: Citation requested in the prompt only

Cheap, but unverified citations can be fabricated or irrelevant. Rejected as insufficient.

## Trade-off Analysis

Verification trades fluency for trust: some answers become "insufficient evidence". For a system that informs real-money
decisions that is the correct default. FinBERT (trained on English financial news, not regulatory filings) is treated as **one**
signal among several and evaluated on a small labelled set before being weighted.

## Consequences

- **Easier:** debugging ("why was this flagged?" resolves to a rule and evidence); regression tests for detectors; auditing LLM output.
- **Harder:** every fact needs a stable id and as-of date (provided by the spine, [ADR-0004](0004-data-spine-and-provenance.md)); chunking must preserve span offsets.
- **To revisit:** entailment check; whether portfolio state / announcements are better modelled as MCP Resources than Tools; OpenTelemetry on custom MCP servers.

## Action Items

1. [ ] P1: define `Finding` schema and evidence-id scheme (`fact:` / `doc:`).
2. [ ] P1: implement metrics, detectors (concentration, drift, fund vs category, cost drag, results-date, sentiment shift, stale data), ranker.
3. [ ] P1: implement narrator with structured output and the citation validator; property-test the validator with adversarial outputs.
4. [ ] P1: announcement reader (RAG over Qdrant) and chat Q&A, both through the validator.
5. [ ] P1: small labelled set to evaluate FinBERT on Indian announcements.
6. [ ] P1: signal ledger and outcome jobs (confirm scope first).
