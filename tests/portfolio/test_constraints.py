from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from stock_quant.domain import Exchange, SecurityId, TradingDay
from stock_quant.portfolio import (
    apply_basic_constraints,
    PortfolioConstructionError,
    PortfolioScore,
    score_weight,
    ScoreMissingPolicy,
    NegativeScorePolicy,
    ZeroScorePolicy,
)
from stock_quant.strategy import (
    BoundaryTiePolicy,
    create_score_intent,
    FeatureScore,
    RankMissingPolicy,
    select_top_n,
)


IDS = tuple(
    SecurityId(code, Exchange.SHANGHAI) for code in ("600000", "600001", "600002")
)
DAY = TradingDay(date(2024, 1, 2))
NOW = datetime(2024, 1, 2, 7, tzinfo=timezone.utc)
HASH = "a" * 64


def test_boundaries_extremes_residual_and_infeasible_inputs() -> None:
    base = score_weight(
        (PortfolioScore(IDS[0], Decimal(9)), PortfolioScore(IDS[1], Decimal(1))),
        cash_target=Decimal(0),
        quantum=Decimal("0.0001"),
        negative_policy=NegativeScorePolicy.REJECT,
        zero_policy=ZeroScorePolicy.ALL_CASH,
        missing_policy=ScoreMissingPolicy.REJECT,
    )
    constrained = apply_basic_constraints(
        base,
        single_name_cap=Decimal("0.4"),
        cash_floor=Decimal("0.2"),
        gross_cap=Decimal("0.7"),
        quantum=Decimal("0.0001"),
    )
    assert max(row.weight for row in constrained.weights) <= Decimal("0.4")
    assert sum((row.weight for row in constrained.weights), Decimal(0)) <= Decimal(
        "0.7"
    )
    assert constrained.cash_weight >= Decimal("0.2")
    with pytest.raises(PortfolioConstructionError, match="parameters"):
        apply_basic_constraints(
            base,
            single_name_cap=Decimal("1.1"),
            cash_floor=Decimal(0),
            gross_cap=Decimal(1),
            quantum=Decimal("0.01"),
        )


def test_strategy_to_portfolio_constraint_boundary_without_fill() -> None:
    feature_rows = tuple(
        FeatureScore(sid, Decimal(index + 1), NOW, HASH)
        for index, sid in enumerate(IDS)
    )
    score_intent = create_score_intent(
        DAY,
        NOW,
        feature_rows,
        universe_identity=HASH,
        config_identity=HASH,
        data_identity=HASH,
    )
    selected = select_top_n(
        score_intent.scores,
        top_n=2,
        ascending=False,
        missing_policy=RankMissingPolicy.REJECT,
        boundary_ties=BoundaryTiePolicy.SECURITY_ID,
    )
    chosen_scores = tuple(
        PortfolioScore(row.security_id, row.value)
        for row in score_intent.scores
        if row.security_id in selected.selected
    )
    portfolio = score_weight(
        chosen_scores,
        cash_target=Decimal("0.1"),
        quantum=Decimal("0.0001"),
        negative_policy=NegativeScorePolicy.REJECT,
        zero_policy=ZeroScorePolicy.ALL_CASH,
        missing_policy=ScoreMissingPolicy.REJECT,
    )
    constrained = apply_basic_constraints(
        portfolio,
        single_name_cap=Decimal("0.5"),
        cash_floor=Decimal("0.1"),
        gross_cap=Decimal("0.9"),
        quantum=Decimal("0.0001"),
    )
    assert sum(
        (target.weight for target in constrained.weights), Decimal(0)
    ) <= Decimal("0.9")
