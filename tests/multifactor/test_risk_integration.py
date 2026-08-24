from datetime import date
from decimal import Decimal

import pytest

from stock_quant.domain import SecurityId, TradingDay
from stock_quant.multifactor.baselines import BaselineCandidate
from stock_quant.multifactor.risk_integration import approve_multifactor_candidate
from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.risk import (
    PITClassification,
    RiskBudgets,
    RiskConfig,
    RiskInfeasibleError,
)


A, B = SecurityId.parse("000001.XSHE"), SecurityId.parse("600000.XSHG")
DAY, HASH = TradingDay(date(2024, 1, 2)), "a" * 64


def config(turnover: str = "1") -> RiskConfig:
    return RiskConfig(
        Decimal(".6"),
        Decimal(".7"),
        Decimal(turnover),
        Decimal(".1"),
        Decimal(".9"),
        Decimal(".0001"),
    )


def test_candidate_must_return_existing_risk_decision_and_integration_identity() -> (
    None
):
    proposed = PortfolioWeights(
        (PortfolioWeight(A, Decimal(".8")), PortfolioWeight(B, Decimal(".2"))),
        Decimal(0),
        Decimal(0),
    )
    candidate = BaselineCandidate("x", proposed, "b" * 64, (str(A), str(B)), "test")
    current = PortfolioWeights((), Decimal(1), Decimal(0))
    facts = (
        PITClassification(A, DAY, "BANK", HASH),
        PITClassification(B, DAY, "TECH", HASH),
    )
    approved = approve_multifactor_candidate(
        candidate,
        as_of=DAY,
        current=current,
        classifications=facts,
        risk_config=config(),
        risk_budgets=RiskBudgets((), ()),
        risk_config_identity=HASH,
        upstream_identity="c" * 64,
    )
    assert approved.decision.request.proposed == candidate.portfolio
    assert approved.decision.output.cash_weight >= Decimal(".1")
    assert (
        approved.intent.decision_day == DAY and len(approved.integration_identity) == 64
    )


def test_pit_classification_mismatch_and_infeasible_turnover_fail_closed() -> None:
    proposed = PortfolioWeights(
        (PortfolioWeight(A, Decimal(1)),), Decimal(0), Decimal(0)
    )
    candidate = BaselineCandidate("x", proposed, "b" * 64, (str(A),), "test")
    current = PortfolioWeights(
        (PortfolioWeight(A, Decimal(1)),), Decimal(0), Decimal(0)
    )
    wrong = PITClassification(A, TradingDay(date(2024, 1, 3)), "BANK", HASH)
    with pytest.raises(ValueError, match="as-of"):
        approve_multifactor_candidate(
            candidate,
            as_of=DAY,
            current=current,
            classifications=(wrong,),
            risk_config=config(),
            risk_budgets=RiskBudgets((), ()),
            risk_config_identity=HASH,
            upstream_identity="c" * 64,
        )
    unsafe_current = PortfolioWeights(
        (PortfolioWeight(A, Decimal(1)),), Decimal(0), Decimal(0)
    )
    zero = PortfolioWeights((PortfolioWeight(A, Decimal(0)),), Decimal(1), Decimal(0))
    zero_candidate = BaselineCandidate("x", zero, "b" * 64, (str(A),), "test")
    with pytest.raises(RiskInfeasibleError):
        approve_multifactor_candidate(
            zero_candidate,
            as_of=DAY,
            current=unsafe_current,
            classifications=(PITClassification(A, DAY, "BANK", HASH),),
            risk_config=config("0"),
            risk_budgets=RiskBudgets((), ()),
            risk_config_identity=HASH,
            upstream_identity="c" * 64,
        )
