"""Fixed ROE quality benchmark with PIT statement revisions."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Tuple
from stock_quant.domain import SecurityId
from stock_quant.features import quality_factors, StatementObservation


@dataclass(frozen=True)
class QualityBenchmarkResult:
    ranked: Tuple[Tuple[SecurityId, Decimal], ...]
    metric: str = "roe"


def run_quality_benchmark(
    statements: Iterable[StatementObservation],
    securities: Iterable[SecurityId],
    *,
    decision_cutoff: datetime,
) -> QualityBenchmarkResult:
    rows = tuple(statements)
    scores = []
    for security in tuple(securities):
        result = quality_factors(
            rows, security_id=security, decision_cutoff=decision_cutoff
        )
        if result.roe is not None:
            scores.append((security, result.roe))
    return QualityBenchmarkResult(
        tuple(sorted(scores, key=lambda item: (-item[1], item[0])))
    )
