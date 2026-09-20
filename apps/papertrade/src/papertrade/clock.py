"""One engine, two clocks (ADR-0003): simulated for backtests, real for forward paper trading."""

from datetime import date, timedelta
from typing import Protocol


class Clock(Protocol):
    def today(self) -> date: ...


class RealClock:
    def today(self) -> date:
        return date.today()


class SimulatedClock:
    """Replays history; time only moves forward, which guards against lookahead by construction."""

    def __init__(self, start: date) -> None:
        self._today = start

    def today(self) -> date:
        return self._today

    def advance(self, days: int = 1) -> date:
        if days < 1:
            raise ValueError("a simulated clock can only move forward")
        self._today += timedelta(days=days)
        return self._today
