from datetime import date, datetime

import pytest

from stock_quant.domain import (
    Exchange,
    ListingLifecycle,
    ListingStatus,
    SecurityId,
)


SECURITY = SecurityId("600000", Exchange.SHANGHAI)


def test_listing_boundaries_use_half_open_interval() -> None:
    lifecycle = ListingLifecycle(
        SECURITY,
        listing_date=date(1999, 11, 10),
        delisting_date=date(2024, 1, 5),
    )

    assert lifecycle.status_as_of(date(1999, 11, 9)) is ListingStatus.PRE_LISTING
    assert lifecycle.status_as_of(date(1999, 11, 10)) is ListingStatus.LISTED
    assert lifecycle.status_as_of(date(2024, 1, 4)) is ListingStatus.LISTED
    assert lifecycle.status_as_of(date(2024, 1, 5)) is ListingStatus.DELISTED
    assert not lifecycle.is_listed_as_of(date(2025, 1, 1))


def test_delisted_identity_retains_queryable_history() -> None:
    lifecycle = ListingLifecycle(
        SECURITY,
        listing_date=date(2000, 1, 1),
        delisting_date=date(2010, 1, 1),
    )

    assert lifecycle.security_id is SECURITY
    assert lifecycle.is_listed_as_of(date(2005, 1, 1))
    assert lifecycle.status_as_of(date(2024, 1, 1)) is ListingStatus.DELISTED


def test_open_ended_listing_remains_listed() -> None:
    lifecycle = ListingLifecycle(SECURITY, listing_date=date(2020, 1, 1))

    assert lifecycle.status_as_of(date(2030, 1, 1)) is ListingStatus.LISTED


@pytest.mark.parametrize(
    "delisting_date", [date(2020, 1, 1), date(2019, 12, 31)]
)
def test_invalid_chronology_is_rejected(delisting_date: date) -> None:
    with pytest.raises(ValueError, match="after listing_date"):
        ListingLifecycle(
            SECURITY,
            listing_date=date(2020, 1, 1),
            delisting_date=delisting_date,
        )


def test_datetime_cannot_silently_change_date_semantics() -> None:
    with pytest.raises(TypeError):
        ListingLifecycle(SECURITY, listing_date=datetime(2020, 1, 1))
    lifecycle = ListingLifecycle(SECURITY, listing_date=date(2020, 1, 1))
    with pytest.raises(TypeError):
        lifecycle.status_as_of(datetime(2020, 1, 1))
