from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from stock_quant.daily.candidates import DailyCandidateSnapshot
from stock_quant.daily.risk_view import generate_portfolio_risk_view
from stock_quant.domain import SecurityId, TradingDay
from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.risk import (
    PITClassification,
    RiskBudgets,
    RiskConfig,
    RiskDecision,
    RiskInfeasibleError,
)


A, B = SecurityId.parse("000001.XSHE"), SecurityId.parse("600000.XSHG")
DAY, HASH = TradingDay(date(2024, 1, 2)), "a" * 64
CANDIDATES = DailyCandidateSnapshot("b" * 64, "c" * 64, (), (A, B), "d" * 64)


def config(turnover: str = "1") -> RiskConfig:
    return RiskConfig(
        Decimal(".6"),
        Decimal(".7"),
        Decimal(turnover),
        Decimal(".1"),
        Decimal(".9"),
        Decimal(".0001"),
    )


def test_view_mandatorily_contains_risk_decision_constraints_and_references() -> None:
    current = PortfolioWeights((), Decimal(1), Decimal(0))
    facts = (
        PITClassification(A, DAY, "BANK", HASH),
        PITClassification(B, DAY, "TECH", HASH),
    )
    view = generate_portfolio_risk_view(
        CANDIDATES,
        as_of=DAY,
        current=current,
        classifications=facts,
        risk_config=config(),
        risk_budgets=RiskBudgets((), ()),
        risk_config_identity=HASH,
        upstream_identity="e" * 64,
        cash_target=Decimal(0),
        quantum=Decimal(".0001"),
        cost_rate_reference=Decimal(".003"),
    )
    assert isinstance(view.decision, RiskDecision)
    assert view.decision.output.cash_weight >= Decimal(".1")
    assert view.approved_turnover <= view.desired_turnover
    assert view.status == "RESEARCH_ONLY_MANUAL_DECISION_REQUIRED"


def test_infeasible_fails_and_module_has_no_trading_side_effect_imports() -> None:
    unsafe = PortfolioWeights((PortfolioWeight(A, Decimal(1)),), Decimal(0), Decimal(0))
    one = DailyCandidateSnapshot("b" * 64, "c" * 64, (), (A,), "d" * 64)
    with pytest.raises(RiskInfeasibleError):
        generate_portfolio_risk_view(
            one,
            as_of=DAY,
            current=unsafe,
            classifications=(PITClassification(A, DAY, "BANK", HASH),),
            risk_config=config("0"),
            risk_budgets=RiskBudgets((), ()),
            risk_config_identity=HASH,
            upstream_identity="e" * 64,
            cash_target=Decimal(1),
            quantum=Decimal(".0001"),
            cost_rate_reference=Decimal(0),
        )
    source = (
        Path(__file__).parents[2] / "src/stock_quant/daily/risk_view.py"
    ).read_text()
    assert "stock_quant.backtest" not in source
    assert "approved_rebalance_intent" not in source
