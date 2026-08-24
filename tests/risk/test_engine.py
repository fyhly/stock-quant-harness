from datetime import date
from decimal import Decimal

from stock_quant.backtest import RebalanceIntent
from stock_quant.domain import Exchange, SecurityId, TradingDay
from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.risk import (
    approved_rebalance_intent,
    create_risk_request,
    NameRiskBudget,
    PITClassification,
    RiskBudgets,
    RiskConfig,
    run_risk_engine,
    SectorRiskBudget,
)


IDS = (SecurityId("600000", Exchange.SHANGHAI), SecurityId("600001", Exchange.SHANGHAI))
DAY = TradingDay(date(2024, 1, 2))
HASH = "a" * 64


def test_budgets_fixed_pipeline_extremes_and_non_bypass_integration() -> None:
    proposed = PortfolioWeights(
        (
            PortfolioWeight(IDS[0], Decimal("0.9")),
            PortfolioWeight(IDS[1], Decimal("0.1")),
        ),
        Decimal(0),
        Decimal(0),
    )
    current = PortfolioWeights((), Decimal(1), Decimal(0))
    facts = tuple(PITClassification(sid, DAY, "BANK", HASH) for sid in IDS)
    request = create_risk_request(
        DAY, proposed, current, facts, config_identity=HASH, upstream_identity=HASH
    )
    budgets = RiskBudgets(
        (NameRiskBudget(IDS[0], Decimal("0.5")),),
        (SectorRiskBudget("BANK", Decimal("0.6")),),
    )
    config = RiskConfig(
        Decimal("0.4"),
        Decimal("0.5"),
        Decimal("0.3"),
        Decimal("0.2"),
        Decimal("0.7"),
        Decimal("0.0001"),
    )
    decision = run_risk_engine(request, config, budgets)
    stages = tuple(dict.fromkeys(row.stage for row in decision.adjustments))
    assert stages == tuple(
        stage
        for stage in ("BUDGET", "SINGLE_NAME", "SECTOR", "TURNOVER", "EXPOSURE")
        if stage in stages
    )
    assert max(row.weight for row in decision.output.weights) <= Decimal("0.4")
    assert decision.output.cash_weight >= Decimal("0.2")
    intent = approved_rebalance_intent("safe-1", decision)
    assert isinstance(intent, RebalanceIntent) and intent.decision_day == DAY


def test_budget_bounds_and_sums_fail_closed() -> None:
    try:
        RiskBudgets((NameRiskBudget(IDS[0], Decimal("1.1")),), ())
    except ValueError:
        pass
    else:
        raise AssertionError("invalid risk budget accepted")
    try:
        RiskBudgets(
            (
                NameRiskBudget(IDS[0], Decimal("0.6")),
                NameRiskBudget(IDS[1], Decimal("0.6")),
            ),
            (),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("excess risk budget sum accepted")
