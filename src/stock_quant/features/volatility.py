"""Explicit trailing realized and downside volatility."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Iterable, Tuple

from stock_quant.domain import SecurityId, TradingCalendar, TradingDay
from stock_quant.features.api import FeatureContractError
from stock_quant.features.momentum import PriceObservation


class MissingReturnPolicy(str, Enum):
    FAIL = "FAIL"


@dataclass(frozen=True)
class VolatilityResult:
    realized: Decimal
    downside: Decimal
    sessions: int
    annualization_sessions: int
    missing_policy: MissingReturnPolicy


def trailing_volatility(
    observations: Iterable[PriceObservation],
    *,
    security_id: SecurityId,
    decision_day: TradingDay,
    decision_cutoff: datetime,
    calendar: TradingCalendar,
    sessions: int,
    annualization_sessions: int = 252,
    minimum_observations: int = 2,
    missing_policy: MissingReturnPolicy = MissingReturnPolicy.FAIL,
) -> VolatilityResult:
    if sessions < minimum_observations or minimum_observations < 2:
        raise FeatureContractError("invalid volatility observation minimum")
    if annualization_sessions <= 0 or missing_policy is not MissingReturnPolicy.FAIL:
        raise FeatureContractError("invalid annualization or missing policy")
    days = tuple(day for day in calendar.trading_days if day < decision_day)
    if len(days) < sessions + 1:
        raise FeatureContractError("insufficient volatility history")
    required = days[-(sessions + 1) :]
    supplied = tuple(observations)
    if any(row.trading_day >= decision_day for row in supplied):
        raise FeatureContractError("decision-day or future close supplied")
    rows = tuple(
        row
        for row in supplied
        if row.security_id == security_id
        and row.trading_day in required
        and row.available_time <= decision_cutoff
    )
    by_day = {row.trading_day: row for row in rows}
    if len(by_day) != len(rows) or tuple(sorted(by_day)) != required:
        raise FeatureContractError(
            "gapped, duplicate, or unavailable volatility history"
        )
    closes = tuple(by_day[day].close for day in required)
    if any(close <= 0 or not close.is_finite() for close in closes):
        raise FeatureContractError("closes must be positive and finite")
    returns: Tuple[Decimal, ...] = tuple(
        current / prior - Decimal(1) for prior, current in zip(closes, closes[1:])
    )
    mean = sum(returns, Decimal(0)) / Decimal(len(returns))
    variance = sum(((value - mean) ** 2 for value in returns), Decimal(0)) / Decimal(
        len(returns)
    )
    downside_variance = sum(
        (min(value, Decimal(0)) ** 2 for value in returns), Decimal(0)
    ) / Decimal(len(returns))
    annualizer = Decimal(annualization_sessions).sqrt()
    return VolatilityResult(
        variance.sqrt() * annualizer,
        downside_variance.sqrt() * annualizer,
        sessions,
        annualization_sessions,
        missing_policy,
    )
