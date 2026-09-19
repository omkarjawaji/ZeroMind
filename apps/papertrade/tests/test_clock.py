from datetime import date

import pytest

from papertrade.clock import RealClock, SimulatedClock


def test_simulated_clock_moves_forward() -> None:
    clock = SimulatedClock(date(2026, 1, 1))
    assert clock.advance() == date(2026, 1, 2)
    assert clock.advance(3) == date(2026, 1, 5)
    assert clock.today() == date(2026, 1, 5)


@pytest.mark.parametrize("days", [0, -1])
def test_simulated_clock_cannot_go_backwards(days: int) -> None:
    clock = SimulatedClock(date(2026, 1, 1))
    with pytest.raises(ValueError):
        clock.advance(days)
    assert clock.today() == date(2026, 1, 1)


def test_real_clock_returns_today() -> None:
    assert RealClock().today() == date.today()
