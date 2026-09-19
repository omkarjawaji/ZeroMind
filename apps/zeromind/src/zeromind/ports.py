"""Provider interfaces (ADR-0001/0004). Sources are swappable and mockable; no live calls in tests.

Broker access here is READ-ONLY by construction: there is no order method on any port in this
package. Execution ports live in ``zeromind_executor``.
"""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal, Protocol

from zeromind.domain import Announcement, Candle, Holding, NavPoint, Transaction
from zeromind.spine import Datum


class BrokerReadPort(Protocol):
    async def holdings(self) -> Datum[list[Holding]]: ...

    async def mf_holdings(self) -> Datum[list[Holding]]: ...

    async def ltp(self, symbols: Sequence[str]) -> Datum[dict[str, Decimal]]: ...


class MarketDataProvider(Protocol):
    async def daily_candles(self, symbol: str, start: date, end: date) -> Datum[list[Candle]]: ...


class FundamentalsProvider(Protocol):
    async def fundamentals(self, symbol: str) -> Datum[dict[str, float]]: ...


class MFDataProvider(Protocol):
    async def nav_history(
        self, scheme_code: str, start: date, end: date
    ) -> Datum[list[NavPoint]]: ...


class AnnouncementsProvider(Protocol):
    async def get_corporate_announcements(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
        source: Literal["auto", "nse", "bse"] = "auto",
    ) -> Datum[list[Announcement]]: ...


class TransactionHistoryImporter(Protocol):
    """Parses a one-time import (Console tradebook CSV, CAS statement) into dated transactions."""

    def parse(self, path: Path) -> list[Transaction]: ...
