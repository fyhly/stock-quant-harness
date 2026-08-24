"""Point-in-time valuation factors with announcement-aware fundamentals."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Optional, Tuple

from stock_quant.domain import SecurityId, TradingDay
from stock_quant.features.api import FeatureContractError


@dataclass(frozen=True)
class FundamentalObservation:
    security_id: SecurityId
    report_period: date
    announcement_time: datetime
    revision_time: datetime
    net_income: Optional[Decimal]
    equity: Optional[Decimal]
    revenue: Optional[Decimal]
    source_identity: str


@dataclass(frozen=True)
class ValuationObservation:
    security_id: SecurityId
    trading_day: TradingDay
    available_time: datetime
    market_cap: Decimal
    source_identity: str


@dataclass(frozen=True)
class ValueFactors:
    pe: Optional[Decimal]
    pb: Optional[Decimal]
    ps: Optional[Decimal]
    earnings_yield: Optional[Decimal]
    report_period: date
    revision_time: datetime
    lineage: Tuple[str, str]


def value_factors(
    valuations: Iterable[ValuationObservation],
    fundamentals: Iterable[FundamentalObservation],
    *,
    security_id: SecurityId,
    decision_day: TradingDay,
    decision_cutoff: datetime,
    maximum_valuation_age_days: int,
) -> ValueFactors:
    values = tuple(valuations)
    facts = tuple(fundamentals)
    if maximum_valuation_age_days < 0:
        raise FeatureContractError("maximum age cannot be negative")
    if any(row.available_time > decision_cutoff for row in values) or any(
        row.announcement_time > decision_cutoff or row.revision_time > decision_cutoff
        for row in facts
    ):
        raise FeatureContractError("future valuation or announcement supplied")
    candidates = tuple(
        row
        for row in values
        if row.security_id == security_id and row.trading_day <= decision_day
    )
    if not candidates:
        raise FeatureContractError("missing valuation")
    valuation = max(candidates, key=lambda row: (row.trading_day, row.available_time))
    if (
        decision_day.value - valuation.trading_day.value
    ).days > maximum_valuation_age_days:
        raise FeatureContractError("stale valuation")
    if valuation.market_cap <= 0 or not valuation.market_cap.is_finite():
        raise FeatureContractError("market cap must be positive and finite")
    available = tuple(row for row in facts if row.security_id == security_id)
    if not available:
        raise FeatureContractError("missing fundamental")
    latest_period = max(row.report_period for row in available)
    revisions = tuple(row for row in available if row.report_period == latest_period)
    selected = max(revisions, key=lambda row: row.revision_time)
    return ValueFactors(
        _ratio(valuation.market_cap, selected.net_income),
        _ratio(valuation.market_cap, selected.equity),
        _ratio(valuation.market_cap, selected.revenue),
        _ratio(selected.net_income, valuation.market_cap),
        selected.report_period,
        selected.revision_time,
        (valuation.source_identity, selected.source_identity),
    )


def _ratio(
    numerator: Optional[Decimal], denominator: Optional[Decimal]
) -> Optional[Decimal]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    if not numerator.is_finite() or not denominator.is_finite():
        raise FeatureContractError("factor inputs must be finite")
    return numerator / denominator
