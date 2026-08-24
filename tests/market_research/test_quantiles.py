from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from stock_quant.market_research.quantiles import quantile_backtests
from stock_quant.research.factor_analytics import FactorAnalyticsError, FactorPoint


DAY = date(2024, 1, 2)
CUTOFF = datetime(2024, 1, 2, 7, tzinfo=timezone.utc)


def row(security: str, score: str, forward: str, *, available: int = 6) -> FactorPoint:
    return FactorPoint(
        security,
        DAY,
        datetime(2024, 1, 2, available, tzinfo=timezone.utc),
        date(2024, 1, 3),
        Decimal(score),
        Decimal(forward),
    )


def test_complete_deterministic_groups_keep_ties_and_apply_declared_cost() -> None:
    rows = (
        row("d", "3", ".4"),
        row("a", "1", ".1"),
        row("c", "2", ".3"),
        row("b", "1", ".2"),
    )
    first = quantile_backtests(
        rows, {DAY: CUTOFF}, quantile_count=3, round_trip_cost_rate=Decimal(".01")
    )
    second = quantile_backtests(
        reversed(rows),
        {DAY: CUTOFF},
        quantile_count=3,
        round_trip_cost_rate=Decimal(".01"),
    )
    assert first == second and len(first) == 3
    assert sum((group.securities for group in first), ()) == ("a", "b", "c", "d")
    assert first[0].securities == ("a", "b") and first[0].gross_return == Decimal(".15")
    assert first[0].net_return == Decimal(".14")


def test_empty_groups_are_explicit_and_future_ranking_is_rejected() -> None:
    groups = quantile_backtests(
        (row("a", "1", ".1"), row("b", "1", ".2")),
        {DAY: CUTOFF},
        quantile_count=3,
        round_trip_cost_rate=Decimal(0),
    )
    assert len(groups) == 3 and sum(not group.securities for group in groups) == 2
    with pytest.raises(FactorAnalyticsError, match="available"):
        quantile_backtests(
            (row("a", "1", ".1", available=8),),
            {DAY: CUTOFF},
            quantile_count=2,
            round_trip_cost_rate=Decimal(0),
        )
