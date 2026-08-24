from decimal import Decimal
from typing import Iterable

import pytest

from stock_quant.domain import Exchange, SecurityId
from stock_quant.portfolio import (
    NegativeScorePolicy,
    PortfolioConstructionError,
    PortfolioScore,
    PortfolioWeights,
    ScoreMissingPolicy,
    score_weight,
    ZeroScorePolicy,
)


IDS = tuple(
    SecurityId(code, Exchange.SHANGHAI) for code in ("600000", "600001", "600002")
)


def calculate(
    rows: Iterable[PortfolioScore],
    negative: NegativeScorePolicy = NegativeScorePolicy.REJECT,
    zero: ZeroScorePolicy = ZeroScorePolicy.ALL_CASH,
    missing: ScoreMissingPolicy = ScoreMissingPolicy.EXCLUDE,
) -> PortfolioWeights:
    return score_weight(
        rows,
        cash_target=Decimal("0.1"),
        quantum=Decimal("0.0001"),
        negative_policy=negative,
        zero_policy=zero,
        missing_policy=missing,
    )


def test_normalization_precision_order_and_missing_exclusion() -> None:
    rows = (
        PortfolioScore(IDS[0], Decimal(1)),
        PortfolioScore(IDS[1], Decimal(2)),
        PortfolioScore(IDS[2], None),
    )
    first = calculate(rows)
    assert first == calculate(reversed(rows))
    assert sum((row.weight for row in first.weights), first.cash_weight) == 1
    assert tuple(row.security_id for row in first.weights) == IDS[:2]


def test_negative_zero_and_missing_policies() -> None:
    negative = (PortfolioScore(IDS[0], Decimal(-1)), PortfolioScore(IDS[1], Decimal(0)))
    with pytest.raises(PortfolioConstructionError, match="negative"):
        calculate(negative)
    cash = calculate(negative, negative=NegativeScorePolicy.FLOOR_ZERO)
    assert cash.cash_weight == 1 and cash.weights == ()
    equal = calculate(
        negative,
        negative=NegativeScorePolicy.FLOOR_ZERO,
        zero=ZeroScorePolicy.EQUAL_WEIGHT,
    )
    assert len(equal.weights) == 2
    with pytest.raises(PortfolioConstructionError, match="missing"):
        calculate((PortfolioScore(IDS[0], None),), missing=ScoreMissingPolicy.REJECT)
