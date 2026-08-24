"""Market IC summaries built on the canonical per-date analytics."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Mapping, Tuple

from stock_quant.research.factor_analytics import (
    DailyFactorAnalytics,
    FactorAnalyticsError,
    FactorPoint,
    factor_analytics,
)


@dataclass(frozen=True)
class MarketICSummary:
    daily: Tuple[DailyFactorAnalytics, ...]
    mean_ic: Decimal
    mean_rank_ic: Decimal
    date_count: int
    convention: str = "EQUAL_WEIGHT_DAILY_CROSS_SECTIONS"


def market_ic_summary(
    points: Iterable[FactorPoint], decision_cutoffs: Mapping[date, datetime]
) -> MarketICSummary:
    daily = factor_analytics(points, decision_cutoffs)
    if not daily:
        raise FactorAnalyticsError("IC summary requires at least one date")
    count = Decimal(len(daily))
    return MarketICSummary(
        daily,
        sum((item.ic for item in daily), Decimal(0)) / count,
        sum((item.rank_ic for item in daily), Decimal(0)) / count,
        len(daily),
    )
