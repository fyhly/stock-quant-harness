from datetime import datetime, timezone
from decimal import Decimal
from typing import Tuple

import pytest

from stock_quant.domain import Exchange, SecurityId
from stock_quant.strategy import (
    BoundaryTiePolicy,
    FeatureScore,
    RankMissingPolicy,
    select_top_n,
    StrategyContractError,
)


IDS = tuple(
    SecurityId(code, Exchange.SHANGHAI)
    for code in ("600000", "600001", "600002", "600003")
)
NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)


def rows() -> Tuple[FeatureScore, ...]:
    return tuple(
        FeatureScore(sid, value, NOW, "a" * 64)
        for sid, value in zip(IDS, (Decimal(2), Decimal(1), Decimal(2), None))
    )


def test_rank_ties_boundary_missing_reasons_and_order_invariance() -> None:
    first = select_top_n(
        rows(),
        top_n=2,
        ascending=True,
        missing_policy=RankMissingPolicy.EXCLUDE,
        boundary_ties=BoundaryTiePolicy.INCLUDE,
    )
    second = select_top_n(
        reversed(rows()),
        top_n=2,
        ascending=True,
        missing_policy=RankMissingPolicy.EXCLUDE,
        boundary_ties=BoundaryTiePolicy.INCLUDE,
    )
    assert first == second
    assert first.selected == IDS[:3]
    assert first.records[0].rank == first.records[2].rank
    assert first.records[-1].reason == "MISSING_SCORE"


def test_exact_boundary_descending_and_missing_reject() -> None:
    exact = select_top_n(
        rows(),
        top_n=2,
        ascending=False,
        missing_policy=RankMissingPolicy.EXCLUDE,
        boundary_ties=BoundaryTiePolicy.SECURITY_ID,
    )
    assert exact.selected == (IDS[0], IDS[2])
    with pytest.raises(StrategyContractError, match="missing"):
        select_top_n(
            rows(),
            top_n=1,
            ascending=True,
            missing_policy=RankMissingPolicy.REJECT,
            boundary_ties=BoundaryTiePolicy.INCLUDE,
        )
