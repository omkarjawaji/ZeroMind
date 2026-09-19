from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from zeromind.spine import Datum, Provenance, fact_id

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def make_provenance(as_of: datetime) -> Provenance:
    return Provenance(source="kite", as_of=as_of, fetched_at=NOW)


def test_fresh_data_is_not_stale() -> None:
    prov = make_provenance(NOW - timedelta(hours=1))
    assert not prov.is_stale(NOW, max_age=timedelta(days=1))


def test_old_data_is_stale() -> None:
    prov = make_provenance(NOW - timedelta(days=3))
    assert prov.is_stale(NOW, max_age=timedelta(days=1))


def test_naive_datetimes_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Provenance(source="kite", as_of=datetime(2026, 9, 20), fetched_at=NOW)


def test_confidence_must_be_between_zero_and_one() -> None:
    with pytest.raises(ValidationError):
        Provenance(source="kite", as_of=NOW, fetched_at=NOW, confidence=1.5)


def test_datum_carries_value_and_provenance() -> None:
    datum = Datum[int](value=7, provenance=make_provenance(NOW))
    assert datum.value == 7
    assert datum.provenance.source == "kite"


def test_fact_id_format() -> None:
    assert (
        fact_id("rolling_return_3y", "fund_x", date(2026, 9, 19))
        == "rolling_return_3y:fund_x@2026-09-19"
    )


@pytest.mark.parametrize("metric", ["Rolling", "has space", "", "a:b"])
def test_fact_id_rejects_bad_metric(metric: str) -> None:
    with pytest.raises(ValueError):
        fact_id(metric, "fund_x", date(2026, 9, 19))


@pytest.mark.parametrize("subject", ["", "has space", "a@b"])
def test_fact_id_rejects_bad_subject(subject: str) -> None:
    with pytest.raises(ValueError):
        fact_id("metric", subject, date(2026, 9, 19))
