from datetime import date
from decimal import Decimal
from pathlib import Path
from stock_quant.domain import TradingDay
from stock_quant.e2e import build_real_allocation

ROOT = Path(__file__).parents[1] / "fixtures" / "real" / "v1"
DAY = TradingDay(date(2024, 11, 29))


def test_scheduled_strategy_portfolio_risk_targets_are_deterministic() -> None:
    first = build_real_allocation(ROOT, DAY)
    assert first == build_real_allocation(ROOT, DAY)
    assert first.rebalance_intent.decision_day == DAY
    assert sum(
        (target.weight for target in first.rebalance_intent.targets), Decimal(0)
    ) <= Decimal("0.8")
    assert first.risk_decision.output.cash_weight >= Decimal("0.2")


def test_risk_is_the_only_rebalance_intent_boundary() -> None:
    closure = build_real_allocation(ROOT, DAY)
    assert closure.risk_decision.request.as_of == closure.rebalance_intent.decision_day
    assert len(closure.rebalance_intent.targets) == 1
