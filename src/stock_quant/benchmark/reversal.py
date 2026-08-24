"""Fixed 5/10-session reversal benchmark."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Tuple
from stock_quant.domain import SecurityId, TradingCalendar, TradingDay
from stock_quant.features import PriceObservation, short_term_reversal


@dataclass(frozen=True)
class ReversalBenchmarkResult:
    scores: Tuple[Tuple[int, Tuple[Tuple[SecurityId, Decimal], ...]], ...]
    sign: str = "negative_trailing_return"


def run_reversal_benchmark(
    observations: Iterable[PriceObservation],
    securities: Iterable[SecurityId],
    *,
    decision_day: TradingDay,
    decision_cutoff: datetime,
    calendar: TradingCalendar,
    view_identity: str,
) -> ReversalBenchmarkResult:
    rows, ids = tuple(observations), tuple(securities)
    return ReversalBenchmarkResult(
        tuple(
            (
                window,
                tuple(
                    sorted(
                        (
                            (
                                security,
                                short_term_reversal(
                                    rows,
                                    security_id=security,
                                    decision_day=decision_day,
                                    decision_cutoff=decision_cutoff,
                                    calendar=calendar,
                                    sessions=window,
                                    view_identity=view_identity,
                                ),
                            )
                            for security in ids
                        ),
                        key=lambda item: (-item[1], item[0]),
                    )
                ),
            )
            for window in (5, 10)
        )
    )
