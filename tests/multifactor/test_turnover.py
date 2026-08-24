from datetime import date
from decimal import Decimal

import pytest

from stock_quant.domain import SecurityId, TradingDay
from stock_quant.multifactor.turnover import audit_turnover
from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.risk import PITClassification, RiskDecision, create_risk_request


A, B = SecurityId.parse("000001.XSHE"), SecurityId.parse("600000.XSHG")
DAY, HASH = TradingDay(date(2024, 1, 2)), "a" * 64


def portfolio(a: str, b: str, cash: str) -> PortfolioWeights:
    weights = tuple(
        PortfolioWeight(security, Decimal(value))
        for security, value in ((A, a), (B, b))
        if Decimal(value) > 0
    )
    return PortfolioWeights(weights, Decimal(cash), Decimal(0))


def decision(
    current: PortfolioWeights, desired: PortfolioWeights, approved: PortfolioWeights
) -> RiskDecision:
    ids = sorted(
        {row.security_id for row in current.weights}
        | {row.security_id for row in desired.weights}
    )
    facts = tuple(PITClassification(item, DAY, "I", HASH) for item in ids)
    request = create_risk_request(
        DAY, desired, current, facts, config_identity=HASH, upstream_identity=HASH
    )
    return RiskDecision(request, approved, (), ())


def test_zero_partial_full_caps_exits_cash_and_precision_are_transparent() -> None:
    current, desired = portfolio(".6", ".4", "0"), portfolio("0", ".5", ".5")
    zero = audit_turnover(
        decision(current, desired, current), configured_cap=Decimal(0)
    )
    partial_output = portfolio(".3", ".45", ".25")
    partial = audit_turnover(
        decision(current, desired, partial_output), configured_cap=Decimal(".3")
    )
    full = audit_turnover(
        decision(current, desired, desired), configured_cap=Decimal(1)
    )
    assert (
        zero.approved_turnover == 0
        and zero.constrained_turnover == zero.desired_turnover
    )
    assert partial.approved_turnover == Decimal(".3")
    assert (
        full.approved_turnover == full.desired_turnover
        and full.constrained_turnover == 0
    )
    assert partial == audit_turnover(
        decision(current, desired, partial_output), configured_cap=Decimal(".3")
    )


def test_decision_that_exceeds_cap_fails_closed() -> None:
    current, desired = portfolio("1", "0", "0"), portfolio("0", "1", "0")
    with pytest.raises(ValueError, match="violates"):
        audit_turnover(
            decision(current, desired, desired), configured_cap=Decimal(".5")
        )
