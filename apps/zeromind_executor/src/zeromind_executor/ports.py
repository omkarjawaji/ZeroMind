"""Executor-side ports (ADR-0002). Only this package may hold broker write capability."""

from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from zeromind_executor.proposal import OrderProposal


class OrderResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    broker_order_id: str | None
    status: Literal["placed", "rejected", "unknown"]


class BrokerExecutionPort(Protocol):
    async def place_order(self, proposal: OrderProposal, tag: str) -> OrderResult: ...

    async def cancel_order(self, broker_order_id: str) -> OrderResult: ...

    async def find_orders_by_tag(self, tag: str) -> list[OrderResult]:
        """Reconcile before any retry: a timeout may have placed the order anyway (L7)."""
        ...


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalChannel(Protocol):
    async def request(self, proposal_hash: str) -> ApprovalDecision: ...
