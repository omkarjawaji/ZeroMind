# ZeroMind

A personal portfolio-intelligence system for Zerodha: a dashboard that explains your stocks and mutual
funds, a paper/strategy lab to validate your own rules, and heavily guarded, human-approved execution
for real orders.

**Design principle:** agents reason and propose; a human approves; deterministic code executes. The read
plane contains no code that can place an order.

Start with [docs/architecture.md](docs/architecture.md) and the decision records in [docs/adr/](docs/adr/).

## Layout

```
apps/
  zeromind/              read plane: data spine, analytics, nudge pipeline, dashboard API
  zeromind_executor/     execution plane: policy engine, approvals, orders (localhost only)
  papertrade/            standalone paper/strategy lab (imports nothing from ZeroMind)
  kite_readonly_proxy/   allowlist proxy exposing only read tools of Kite MCP
  announcements_mcp/     own NSE/BSE announcements MCP server
tests/architecture/      CI-enforced boundary rules from the ADRs
docs/                    architecture overview + ADRs
```

## Development

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11+.

```bash
uv sync --all-packages     # install every app plus dev tools into .venv
uv run ruff check .        # lint
uv run pytest              # tests, including architecture boundary tests
```

The workspace installs all apps into one environment for development only. In deployment the read plane
and the executor run as separate processes with separate settings and secrets.

## Status

v0.1 architecture and P0 skeleton. No live broker calls are made anywhere yet.
