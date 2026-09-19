"""Provisional domain models.

Shapes will be revised after the P0 verification of Kite MCP response formats (ADR-0004).
New instrument kinds (ETF, gold, bond) are added later as enum members plus analyzers.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class InstrumentKind(StrEnum):
    EQUITY = "equity"
    MF = "mf"


class TradeSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class Instrument(_Frozen):
    kind: InstrumentKind
    symbol: str
    name: str | None = None


class Holding(_Frozen):
    instrument: Instrument
    quantity: Decimal
    average_price: Decimal
    last_price: Decimal | None = None


class Candle(_Frozen):
    day: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class NavPoint(_Frozen):
    day: date
    nav: Decimal


class Announcement(_Frozen):
    id: str
    symbol: str
    published_at: datetime
    headline: str
    url: str | None = None
    body: str | None = None


class Transaction(_Frozen):
    """A dated cash flow from an imported tradebook/CAS; needed for XIRR and holding periods."""

    instrument: Instrument
    trade_date: date
    side: TradeSide
    quantity: Decimal
    price: Decimal
