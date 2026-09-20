from decimal import Decimal

import pytest
from pydantic import ValidationError

from zeromind_executor.modes import DEFAULT_MODE, ExecutionMode, places_real_orders
from zeromind_executor.proposal import OrderProposal


def make(**overrides: object) -> OrderProposal:
    fields: dict[str, object] = {
        "exchange": "NSE",
        "symbol": "RELIANCE",
        "side": "BUY",
        "quantity": 10,
        "limit_price": Decimal("2500.00"),
    }
    fields.update(overrides)
    return OrderProposal(**fields)  # type: ignore[arg-type]


def test_hash_is_deterministic() -> None:
    assert make().proposal_hash() == make().proposal_hash()


@pytest.mark.parametrize(
    "change",
    [{"quantity": 11}, {"side": "SELL"}, {"symbol": "TCS"}, {"limit_price": Decimal("2500.05")}],
)
def test_any_field_change_alters_the_hash(change: dict[str, object]) -> None:
    assert make(**change).proposal_hash() != make().proposal_hash()


def test_equal_prices_hash_identically_regardless_of_representation() -> None:
    assert (
        make(limit_price=Decimal("2500")).proposal_hash()
        == make(limit_price=Decimal("2500.00")).proposal_hash()
    )


def test_proposal_is_immutable() -> None:
    proposal = make()
    with pytest.raises(ValidationError):
        proposal.quantity = 99  # type: ignore[misc]


@pytest.mark.parametrize(
    "bad",
    [
        {"order_type": "MARKET"},
        {"product": "MIS"},
        {"product": "NRML"},
        {"validity": "IOC"},
        {"quantity": 0},
        {"quantity": -5},
        {"quantity": 1.5},
        {"limit_price": Decimal("0")},
        {"limit_price": Decimal("-1")},
        {"limit_price": Decimal("NaN")},
        {"symbol": "reliance"},
        {"exchange": "NFO"},
    ],
)
def test_out_of_scope_orders_cannot_be_constructed(bad: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        make(**bad)


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        make(trigger_price=Decimal("1"))


def test_order_tag_is_twenty_chars_and_stable() -> None:
    tag = make().order_tag()
    assert len(tag) == 20
    assert tag.startswith("ZM")
    assert tag == make().order_tag()


def test_default_mode_is_paper_and_only_live_places_real_orders() -> None:
    assert DEFAULT_MODE is ExecutionMode.PAPER
    assert [m for m in ExecutionMode if places_real_orders(m)] == [ExecutionMode.LIVE]
