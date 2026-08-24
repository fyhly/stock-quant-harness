from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from stock_quant.research.factor_analytics import (
    FactorAnalyticsError,
    FactorPoint,
    factor_analytics,
)


DAY = date(2024, 1, 2)
CUTOFF = datetime(2024, 1, 2, 7, tzinfo=timezone.utc)


def point(security: str, score: str, result: str, *, day: date = DAY) -> FactorPoint:
    return FactorPoint(
        security,
        day,
        datetime(day.year, day.month, day.day, 6, tzinfo=timezone.utc),
        date(2024, 1, 3) if day == DAY else date(2024, 1, 5),
        Decimal(score),
        Decimal(result),
    )


def test_cross_sectional_ic_rank_ic_quantiles_and_order_are_deterministic() -> None:
    rows = (point("b", "2", "0.2"), point("a", "1", "0.1"))
    first = factor_analytics(rows, {DAY: CUTOFF}, quantile_count=2)
    second = factor_analytics(reversed(rows), {DAY: CUTOFF}, quantile_count=2)
    assert first == second
    assert first[0].ic == Decimal(1)
    assert first[0].rank_ic == Decimal(1)
    assert tuple(item.mean_forward_return for item in first[0].quantiles) == (
        Decimal("0.1"),
        Decimal("0.2"),
    )


def test_dates_remain_separate_and_pit_alignment_is_enforced() -> None:
    later = date(2024, 1, 4)
    result = factor_analytics(
        (
            point("a", "1", "0.1"),
            point("b", "2", "0.2"),
            point("a", "2", "0.3", day=later),
            point("b", "1", "0.1", day=later),
        ),
        {DAY: CUTOFF, later: datetime(2024, 1, 4, 7, tzinfo=timezone.utc)},
    )
    assert tuple(item.feature_date for item in result) == (DAY, later)

    future = FactorPoint(
        "x",
        DAY,
        datetime(2024, 1, 2, 8, tzinfo=timezone.utc),
        date(2024, 1, 3),
        Decimal(1),
        Decimal(1),
    )
    with pytest.raises(FactorAnalyticsError, match="available"):
        factor_analytics((future, point("y", "2", "2")), {DAY: CUTOFF})


def test_insufficient_constant_and_non_forward_samples_fail_closed() -> None:
    with pytest.raises(FactorAnalyticsError, match="at least two"):
        factor_analytics((point("a", "1", "1"),), {DAY: CUTOFF})
    with pytest.raises(FactorAnalyticsError, match="constant"):
        factor_analytics((point("a", "1", "1"), point("b", "1", "2")), {DAY: CUTOFF})
    invalid = FactorPoint("a", DAY, CUTOFF, DAY, Decimal(1), Decimal(1))
    with pytest.raises(FactorAnalyticsError, match="after"):
        factor_analytics((invalid, point("b", "2", "2")), {DAY: CUTOFF})
