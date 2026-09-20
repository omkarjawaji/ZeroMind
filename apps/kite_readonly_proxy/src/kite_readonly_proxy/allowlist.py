"""Deny-by-default tool policy for the read-only Kite MCP proxy (ADR-0002 L1).

Tool names come from the Kite MCP tool list observed during design; verify against the live
server in P0. Anything not explicitly allowed is denied, so a newly added upstream tool stays
blocked until someone reviews it.
"""

READ_TOOLS = frozenset(
    {
        "get_holdings",
        "get_mf_holdings",
        "get_positions",
        "get_margins",
        "get_profile",
        "get_quotes",
        "get_ltp",
        "get_ohlc",
        "get_historical_data",
        "get_orders",
        "get_order_history",
        "get_order_trades",
        "get_trades",
        "get_gtts",
        "search_instruments",
    }
)

# Starting a Kite session does not move money; the daily login is also a natural arming step.
SESSION_TOOLS = frozenset({"login"})

# Documented for tests and reviewers. Only the executor may ever call these.
WRITE_TOOLS = frozenset(
    {
        "place_order",
        "modify_order",
        "cancel_order",
        "place_gtt_order",
        "modify_gtt_order",
        "delete_gtt_order",
    }
)

ALLOWED_TOOLS = READ_TOOLS | SESSION_TOOLS


def is_allowed(tool_name: str) -> bool:
    return tool_name in ALLOWED_TOOLS
