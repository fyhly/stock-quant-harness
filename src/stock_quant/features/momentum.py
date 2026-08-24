"""Session-exact trailing momentum from explicitly identified price views."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from stock_quant.domain import SecurityId, TradingCalendar, TradingDay
from stock_quant.features.api import FeatureContractError


@dataclass(frozen=True)
class PriceObservation:
    security_id: SecurityId
    trading_day: TradingDay
    close: Decimal
    available_time: datetime
    view_identity: str


def trailing_return(
    observations: Iterable[PriceObservation],
    *,
    security_id: SecurityId,
    decision_day: TradingDay,
    decision_cutoff: datetime,
    calendar: TradingCalendar,
    sessions: int,
    view_identity: str,
) -> Decimal:
    if sessions not in (20, 60, 120):
        raise FeatureContractError("momentum sessions must be 20, 60, or 120")
    eligible_days = tuple(day for day in calendar.trading_days if day < decision_day)
    if len(eligible_days) < sessions + 1:
        raise FeatureContractError("insufficient momentum history")
    required = eligible_days[-(sessions + 1) :]
    rows = tuple(
        row
        for row in observations
        if row.security_id == security_id
        and row.trading_day in required
        and row.available_time <= decision_cutoff
    )
    if any(row.trading_day >= decision_day for row in observations):
        raise FeatureContractError("decision-day or future close supplied")
    if any(row.view_identity != view_identity for row in rows):
        raise FeatureContractError("mixed or undeclared price view")
    by_day = {row.trading_day: row for row in rows}
    if len(by_day) != len(rows) or tuple(sorted(by_day)) != required:
        raise FeatureContractError("gapped, duplicate, or unavailable momentum history")
    if any(row.close <= 0 or not row.close.is_finite() for row in rows):
        raise FeatureContractError("prices must be positive finite Decimals")
    return by_day[required[-1]].close / by_day[required[0]].close - Decimal(1)
