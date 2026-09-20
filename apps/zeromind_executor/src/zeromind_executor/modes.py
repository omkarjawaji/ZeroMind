"""Execution modes (ADR-0002 L8). LIVE is disarmed by default; the default mode is PAPER."""

from enum import StrEnum


class ExecutionMode(StrEnum):
    OFF = "off"
    PAPER = "paper"
    READ_ONLY = "read_only"
    LIVE = "live"


DEFAULT_MODE = ExecutionMode.PAPER


def places_real_orders(mode: ExecutionMode) -> bool:
    """Only LIVE may reach the broker's write tools."""
    return mode is ExecutionMode.LIVE
