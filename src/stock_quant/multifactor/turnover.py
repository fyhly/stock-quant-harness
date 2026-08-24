"""Transparent desired-versus-risk-approved turnover evidence."""

from dataclasses import dataclass
from decimal import Decimal

from stock_quant.portfolio import PortfolioWeights
from stock_quant.risk import RiskDecision


@dataclass(frozen=True)
class TurnoverAudit:
    decision: RiskDecision
    configured_cap: Decimal
    desired_turnover: Decimal
    approved_turnover: Decimal
    constrained_turnover: Decimal


def audit_turnover(decision: RiskDecision, *, configured_cap: Decimal) -> TurnoverAudit:
    if not configured_cap.is_finite() or not Decimal(0) <= configured_cap <= Decimal(1):
        raise ValueError("turnover cap must be in [0, 1]")
    desired = _turnover(decision.request.proposed, decision.request.current)
    approved = _turnover(decision.output, decision.request.current)
    if approved > configured_cap or approved > desired:
        raise ValueError("RiskDecision violates configured turnover evidence")
    return TurnoverAudit(
        decision, configured_cap, desired, approved, desired - approved
    )


def _turnover(left: PortfolioWeights, right: PortfolioWeights) -> Decimal:
    left_map = {row.security_id: row.weight for row in left.weights}
    right_map = {row.security_id: row.weight for row in right.weights}
    securities = set(left_map) | set(right_map)
    distance = sum(
        (
            abs(left_map.get(item, Decimal(0)) - right_map.get(item, Decimal(0)))
            for item in securities
        ),
        Decimal(0),
    )
    return (distance + abs(left.cash_weight - right.cash_weight)) / Decimal(2)
