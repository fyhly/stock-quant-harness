from datetime import date, datetime

import pytest

from stock_quant.domain import Exchange, ListingLifecycle, SecurityId
from stock_quant.universe import ExclusionCode, ListingHistoryFilter


SECURITY = SecurityId("600000", Exchange.SHANGHAI)


def test_point_in_time_listing_boundaries_and_retained_history() -> None:
    lifecycle = ListingLifecycle(
        SECURITY, date(2000, 1, 2), delisting_date=date(2010, 1, 3)
    )
    rule = ListingHistoryFilter({SECURITY: lifecycle})

    pre_listing = rule.evaluate(SECURITY, date(2000, 1, 1))
    assert pre_listing.exclusion is not None
    assert pre_listing.exclusion.code is ExclusionCode.PRE_LISTING
    assert rule.evaluate(SECURITY, date(2000, 1, 2)).eligible
    assert rule.evaluate(SECURITY, date(2010, 1, 2)).eligible
    delisted = rule.evaluate(SECURITY, date(2010, 1, 3))
    assert delisted.exclusion is not None
    assert delisted.exclusion.code is ExclusionCode.DELISTED
    assert delisted.exclusion.evidence == (("delisting_date", "2010-01-03"),)
    # A later delisted state does not contaminate the historical listed query.
    assert rule.evaluate(SECURITY, date(2005, 1, 1)).eligible


def test_missing_history_fails_closed() -> None:
    decision = ListingHistoryFilter({}).evaluate(SECURITY, date(2020, 1, 1))

    assert not decision.eligible
    assert decision.exclusion is not None
    assert decision.exclusion.code is ExclusionCode.MISSING_LISTING_HISTORY


def test_mismatched_identity_and_datetime_are_rejected() -> None:
    other = SecurityId("000001", Exchange.SHENZHEN)
    with pytest.raises(ValueError, match="identity"):
        ListingHistoryFilter({SECURITY: ListingLifecycle(other, date(2000, 1, 1))})
    rule = ListingHistoryFilter(
        {SECURITY: ListingLifecycle(SECURITY, date(2000, 1, 1))}
    )
    with pytest.raises(TypeError, match="date"):
        rule.evaluate(SECURITY, datetime(2020, 1, 1))
