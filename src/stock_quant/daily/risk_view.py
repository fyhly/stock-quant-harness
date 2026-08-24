"""RiskEngine-approved daily portfolio research view with no trading side effects."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from stock_quant.daily.candidates import DailyCandidateSnapshot
from stock_quant.domain import TradingDay
from stock_quant.portfolio import PortfolioWeights, equal_weight
from stock_quant.risk import (
    PITClassification,
    RiskBudgets,
    RiskConfig,
    RiskDecision,
    create_risk_request,
    run_risk_engine,
)


@dataclass(frozen=True)
class DailyPortfolioResearchView:
    candidate_identity: str
    decision: RiskDecision
    desired_turnover: Decimal
    approved_turnover: Decimal
    cost_rate_reference: Decimal
    status: str = "RESEARCH_ONLY_MANUAL_DECISION_REQUIRED"


def generate_portfolio_risk_view(
    candidates: DailyCandidateSnapshot,
    *,
    as_of: TradingDay,
    current: PortfolioWeights,
    classifications: Iterable[PITClassification],
    risk_config: RiskConfig,
    risk_budgets: RiskBudgets,
    risk_config_identity: str,
    upstream_identity: str,
    cash_target: Decimal,
    quantum: Decimal,
    cost_rate_reference: Decimal,
) -> DailyPortfolioResearchView:
    if cost_rate_reference < 0 or not cost_rate_reference.is_finite():
        raise ValueError("cost reference must be nonnegative finite")
    proposed = equal_weight(
        candidates.selected, cash_target=cash_target, quantum=quantum
    )
    request = create_risk_request(
        as_of,
        proposed,
        current,
        classifications,
        config_identity=risk_config_identity,
        upstream_identity=upstream_identity,
    )
    decision = run_risk_engine(request, risk_config, risk_budgets)
    return DailyPortfolioResearchView(
        candidates.snapshot_identity,
        decision,
        _turnover(proposed, current),
        _turnover(decision.output, current),
        cost_rate_reference,
    )


def _turnover(left: PortfolioWeights, right: PortfolioWeights) -> Decimal:
    left_map = {row.security_id: row.weight for row in left.weights}
    right_map = {row.security_id: row.weight for row in right.weights}
    keys = set(left_map) | set(right_map)
    distance = sum(
        (
            abs(left_map.get(key, Decimal(0)) - right_map.get(key, Decimal(0)))
            for key in keys
        ),
        Decimal(0),
    )
    return (distance + abs(left.cash_weight - right.cash_weight)) / Decimal(2)
