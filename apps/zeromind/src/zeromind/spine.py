"""Provenance-tagged data spine primitives (ADR-0004).

Every stored datum carries where it came from and how fresh it is, so the UI can drill down to
the source and the LLM layer can cite stable fact ids (ADR-0005).
"""

import re
from datetime import date, datetime, timedelta
from typing import Generic, TypeVar

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

T = TypeVar("T")


class Provenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = Field(min_length=1)
    as_of: AwareDatetime
    fetched_at: AwareDatetime
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    def age(self, now: datetime) -> timedelta:
        return now - self.as_of

    def is_stale(self, now: datetime, max_age: timedelta) -> bool:
        return self.age(now) > max_age


class Datum(BaseModel, Generic[T]):
    """A value together with its provenance. Sources degrade to 'stale', never to silently wrong."""

    model_config = ConfigDict(frozen=True)

    value: T
    provenance: Provenance


_METRIC = re.compile(r"^[a-z0-9_]+$")
_SUBJECT = re.compile(r"^[A-Za-z0-9_.&-]+$")


def fact_id(metric: str, subject: str, as_of: date) -> str:
    """Stable id for a computed fact, e.g. ``rolling_return_3y:fund_x@2026-09-19``.

    Used as the ``id`` of ``fact`` citations; the citation validator checks ids against the
    evidence set supplied for a request.
    """
    if not _METRIC.match(metric):
        raise ValueError(f"invalid metric name: {metric!r}")
    if not _SUBJECT.match(subject):
        raise ValueError(f"invalid subject: {subject!r}")
    return f"{metric}:{subject}@{as_of.isoformat()}"
