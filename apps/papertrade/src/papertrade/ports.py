"""Lab ports (ADR-0003). The lab has no code path to order placement: it can only emit signals."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal, Protocol


@dataclass(frozen=True)
class Bar:
    day: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(frozen=True)
class Signal:
    symbol: str
    action: Literal["enter", "exit"]


@dataclass(frozen=True)
class Fill:
    symbol: str
    day: date
    side: Literal["buy", "sell"]
    quantity: int
    price: Decimal
    charges: Decimal


class MarketDataPort(Protocol):
    def bars(self, symbol: str, start: date, end: date) -> Sequence[Bar]: ...


class Strategy(Protocol):
    def on_bar(self, symbol: str, history: Sequence[Bar]) -> Signal | None:
        """``history`` holds only bars up to and including the decision day (no lookahead)."""
        ...


class FillModel(Protocol):
    def fill(self, signal: Signal, quantity: int, next_bar: Bar) -> Fill:
        """Signals fill at the NEXT bar's open, with slippage and charges applied."""
        ...


class Ledger(Protocol):
    def record(self, fill: Fill) -> None: ...

    def cash(self) -> Decimal: ...
