"""Immutable, hashable order proposal (ADR-0002 L0 and L3).

The type itself enforces v1 scope: delivery (CNC) limit orders valid for the day. Market orders,
intraday/margin products and derivatives cannot be constructed. Approval signs ``proposal_hash``;
the executor recomputes it and rejects on mismatch, so an approved order cannot be altered.
"""

import hashlib
import json
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_PRICE_QUANTUM = Decimal("0.01")


class OrderProposal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    exchange: Literal["NSE", "BSE"]
    symbol: str = Field(pattern=r"^[A-Z0-9&-]{1,20}$")
    side: Literal["BUY", "SELL"]
    quantity: int = Field(gt=0, strict=True)
    limit_price: Decimal
    order_type: Literal["LIMIT"] = "LIMIT"
    product: Literal["CNC"] = "CNC"
    validity: Literal["DAY"] = "DAY"

    @field_validator("limit_price")
    @classmethod
    def _normalise_price(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value <= 0:
            raise ValueError("limit_price must be a positive, finite number")
        # Fixed two-decimal form so equal prices always hash identically ("10" == "10.00").
        return value.quantize(_PRICE_QUANTUM)

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def proposal_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def order_tag(self) -> str:
        """Idempotency tag sent as the broker order tag ('ZM' + 18 hex chars = 20 chars).

        The broker's tag length/charset limits are to be verified in P0.
        """
        return "ZM" + self.proposal_hash()[:18]
