from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from stock_quant.market_research.ic import market_ic_summary
from stock_quant.research.factor_analytics import FactorAnalyticsError, FactorPoint


def row(day: int, security: str, score: str, forward: str) -> FactorPoint:
    feature_date = date(2024, 1, day)
    return FactorPoint(
        security,
        feature_date,
        datetime(2024, 1, day, 6, tzinfo=timezone.utc),
        date(2024, 1, day + 1),
        Decimal(score),
        Decimal(forward),
    )


def test_ic_is_calculated_and_aggregated_only_within_each_date() -> None:
    rows = (
        row(2, "a", "1", "1"),
        row(2, "b", "2", "2"),
        row(3, "a", "1", "2"),
        row(3, "b", "2", "1"),
    )
    cutoffs = {
        date(2024, 1, day): datetime(2024, 1, day, 7, tzinfo=timezone.utc)
        for day in (2, 3)
    }
    summary = market_ic_summary(rows, cutoffs)
    assert tuple(item.ic for item in summary.daily) == (Decimal(1), Decimal(-1))
    assert summary.mean_ic == summary.mean_rank_ic == 0 and summary.date_count == 2


def test_insufficient_missing_and_future_available_rows_fail_closed() -> None:
    cutoff = {date(2024, 1, 2): datetime(2024, 1, 2, 7, tzinfo=timezone.utc)}
    with pytest.raises(FactorAnalyticsError, match="at least two"):
        market_ic_summary((row(2, "a", "1", "1"),), cutoff)
    future = FactorPoint(
        "a",
        date(2024, 1, 2),
        datetime(2024, 1, 2, 8, tzinfo=timezone.utc),
        date(2024, 1, 3),
        Decimal(1),
        Decimal(1),
    )
    with pytest.raises(FactorAnalyticsError, match="available"):
        market_ic_summary((future, row(2, "b", "2", "2")), cutoff)
