"""Fixed 20-session realized/downside low-vol benchmark."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Tuple
from stock_quant.domain import SecurityId, TradingCalendar, TradingDay
from stock_quant.features import PriceObservation, trailing_volatility


@dataclass(frozen=True)
class LowVolScore:
    security_id: SecurityId
    realized: Decimal
    downside: Decimal


@dataclass(frozen=True)
class LowVolBenchmarkResult:
    window: int
    annualization: int
    ranked: Tuple[LowVolScore, ...]


def run_low_vol_benchmark(
    observations: Iterable[PriceObservation],
    securities: Iterable[SecurityId],
    *,
    decision_day: TradingDay,
    decision_cutoff: datetime,
    calendar: TradingCalendar,
) -> LowVolBenchmarkResult:
    rows = tuple(observations)
    scores = []
    for security in tuple(securities):
        result = trailing_volatility(
            rows,
            security_id=security,
            decision_day=decision_day,
            decision_cutoff=decision_cutoff,
            calendar=calendar,
            sessions=20,
            annualization_sessions=252,
            minimum_observations=20,
        )
        scores.append(LowVolScore(security, result.realized, result.downside))
    return LowVolBenchmarkResult(
        20,
        252,
        tuple(
            sorted(
                scores, key=lambda row: (row.realized, row.downside, row.security_id)
            )
        ),
    )
