"""Explicit score-proportional portfolio weighting policies."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from enum import Enum
from typing import Iterable, Optional

from stock_quant.domain import SecurityId
from stock_quant.portfolio.equal_weight import (
    equal_weight,
    PortfolioConstructionError,
    PortfolioWeight,
    PortfolioWeights,
)


class NegativeScorePolicy(str, Enum):
    REJECT = "REJECT"
    FLOOR_ZERO = "FLOOR_ZERO"


class ZeroScorePolicy(str, Enum):
    ALL_CASH = "ALL_CASH"
    EQUAL_WEIGHT = "EQUAL_WEIGHT"


class ScoreMissingPolicy(str, Enum):
    EXCLUDE = "EXCLUDE"
    REJECT = "REJECT"


@dataclass(frozen=True)
class PortfolioScore:
    security_id: SecurityId
    score: Optional[Decimal]


def score_weight(
    scores: Iterable[PortfolioScore],
    *,
    cash_target: Decimal,
    quantum: Decimal,
    negative_policy: NegativeScorePolicy,
    zero_policy: ZeroScorePolicy,
    missing_policy: ScoreMissingPolicy,
) -> PortfolioWeights:
    if (
        not cash_target.is_finite()
        or not Decimal(0) <= cash_target <= Decimal(1)
        or not quantum.is_finite()
        or quantum <= 0
    ):
        raise PortfolioConstructionError("invalid cash target or quantum")
    rows = tuple(sorted(scores, key=lambda row: row.security_id))
    ids = tuple(row.security_id for row in rows)
    if not rows or len(ids) != len(set(ids)):
        raise PortfolioConstructionError("scores must be non-empty and unique")
    if missing_policy is ScoreMissingPolicy.REJECT and any(
        row.score is None for row in rows
    ):
        raise PortfolioConstructionError("missing score rejected by policy")
    observed = tuple(row for row in rows if row.score is not None)
    if any(not row.score.is_finite() for row in observed if row.score is not None):
        raise PortfolioConstructionError("scores must be finite")
    if negative_policy is NegativeScorePolicy.REJECT and any(
        row.score < 0 for row in observed if row.score is not None
    ):
        raise PortfolioConstructionError("negative score rejected by policy")
    transformed = tuple(
        (row.security_id, max(row.score, Decimal(0)))
        for row in observed
        if row.score is not None
    )
    total = sum((value for _, value in transformed), Decimal(0))
    if total == 0:
        if zero_policy is ZeroScorePolicy.ALL_CASH:
            return PortfolioWeights((), Decimal(1), Decimal(1) - cash_target)
        return equal_weight(
            (security for security, _ in transformed),
            cash_target=cash_target,
            quantum=quantum,
        )
    investable = Decimal(1) - cash_target
    raw = tuple(
        (security, investable * value / total) for security, value in transformed
    )
    rounded = tuple(
        (security, value.quantize(quantum, rounding=ROUND_DOWN))
        for security, value in raw
    )
    residual = investable - sum((value for _, value in rounded), Decimal(0))
    weights = tuple(
        PortfolioWeight(security, value + (residual if index == 0 else Decimal(0)))
        for index, (security, value) in enumerate(rounded)
    )
    return PortfolioWeights(weights, cash_target, residual)
