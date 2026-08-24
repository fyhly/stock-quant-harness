"""Fixed earnings-yield value benchmark with PIT announcements."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Tuple
from stock_quant.domain import SecurityId, TradingDay
from stock_quant.features import (
    FundamentalObservation,
    ValuationObservation,
    value_factors,
)


@dataclass(frozen=True)
class ValueBenchmarkResult:
    ranked: Tuple[Tuple[SecurityId, Decimal], ...]
    metric: str = "earnings_yield"


def run_value_benchmark(
    valuations: Iterable[ValuationObservation],
    fundamentals: Iterable[FundamentalObservation],
    securities: Iterable[SecurityId],
    *,
    decision_day: TradingDay,
    decision_cutoff: datetime,
) -> ValueBenchmarkResult:
    values, facts = tuple(valuations), tuple(fundamentals)
    scores = []
    for security in tuple(securities):
        result = value_factors(
            values,
            facts,
            security_id=security,
            decision_day=decision_day,
            decision_cutoff=decision_cutoff,
            maximum_valuation_age_days=5,
        )
        if result.earnings_yield is not None:
            scores.append((security, result.earnings_yield))
    return ValueBenchmarkResult(
        tuple(sorted(scores, key=lambda item: (-item[1], item[0])))
    )
