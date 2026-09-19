import pytest

from kite_readonly_proxy.allowlist import ALLOWED_TOOLS, READ_TOOLS, WRITE_TOOLS, is_allowed


def test_no_write_tool_is_allowed() -> None:
    assert not ALLOWED_TOOLS & WRITE_TOOLS


@pytest.mark.parametrize("tool", sorted(WRITE_TOOLS))
def test_write_tools_are_denied(tool: str) -> None:
    assert not is_allowed(tool)


@pytest.mark.parametrize("tool", sorted(READ_TOOLS))
def test_read_tools_are_allowed(tool: str) -> None:
    assert is_allowed(tool)


@pytest.mark.parametrize("tool", ["", "PLACE_ORDER", "place_order ", "get_holdings; place_order"])
def test_unknown_or_malformed_names_are_denied(tool: str) -> None:
    assert not is_allowed(tool)


def test_read_tools_cannot_look_like_writes() -> None:
    write_prefixes = ("place_", "modify_", "cancel_", "delete_")
    assert not [t for t in ALLOWED_TOOLS if t.startswith(write_prefixes)]
