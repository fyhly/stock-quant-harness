"""Mandatory existing RiskEngine path for every multi-factor candidate."""

from dataclasses import dataclass
import hashlib
from typing import Iterable

from stock_quant.backtest import RebalanceIntent
from stock_quant.domain import TradingDay
from stock_quant.multifactor.baselines import BaselineCandidate
from stock_quant.portfolio import PortfolioWeights
from stock_quant.risk import (
    PITClassification,
    RiskBudgets,
    RiskConfig,
    RiskDecision,
    approved_rebalance_intent,
    create_risk_request,
    run_risk_engine,
)


@dataclass(frozen=True)
class RiskApprovedCandidate:
    candidate: BaselineCandidate
    decision: RiskDecision
    intent: RebalanceIntent
    integration_identity: str


def approve_multifactor_candidate(
    candidate: BaselineCandidate,
    *,
    as_of: TradingDay,
    current: PortfolioWeights,
    classifications: Iterable[PITClassification],
    risk_config: RiskConfig,
    risk_budgets: RiskBudgets,
    risk_config_identity: str,
    upstream_identity: str,
) -> RiskApprovedCandidate:
    request = create_risk_request(
        as_of,
        candidate.portfolio,
        current,
        classifications,
        config_identity=risk_config_identity,
        upstream_identity=upstream_identity,
    )
    decision = run_risk_engine(request, risk_config, risk_budgets)
    integration_identity = hashlib.sha256(
        f"{candidate.config_identity}|{risk_config_identity}|{upstream_identity}".encode()
    ).hexdigest()
    intent = approved_rebalance_intent(
        f"multifactor-{integration_identity[:16]}", decision
    )
    return RiskApprovedCandidate(candidate, decision, intent, integration_identity)
