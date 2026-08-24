from datetime import date
from decimal import Decimal

import pytest

from stock_quant.domain import Exchange, SecurityId, TradingDay
from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.risk import (
    approved_rebalance_intent,
    create_risk_request,
    PITClassification,
    RiskBudgets,
    RiskConfig,
    RiskInfeasibleError,
    RiskRequest,
    run_risk_engine,
)


IDS = (SecurityId("600000", Exchange.SHANGHAI), SecurityId("600001", Exchange.SHANGHAI))
DAY = TradingDay(date(2024, 1, 2))
HASH = "a" * 64
SAFE = PortfolioWeights(
    (PortfolioWeight(IDS[1], Decimal("0.4")),), Decimal("0.6"), Decimal(0)
)
CONFIG = RiskConfig(
    Decimal("0.4"),
    Decimal("0.5"),
    Decimal(1),
    Decimal("0.2"),
    Decimal("0.8"),
    Decimal("0.0001"),
)


def request(
    current: PortfolioWeights, proposed: PortfolioWeights = SAFE
) -> RiskRequest:
    names = sorted(
        {row.security_id for row in current.weights}
        | {row.security_id for row in proposed.weights}
    )
    facts = tuple(PITClassification(sid, DAY, "BANK", HASH) for sid in names)
    return create_risk_request(
        DAY, proposed, current, facts, config_identity=HASH, upstream_identity=HASH
    )


def test_unsafe_current_zero_or_insufficient_turnover_fails_closed() -> None:
    unsafe = PortfolioWeights(
        (PortfolioWeight(IDS[0], Decimal("0.9")),), Decimal("0.1"), Decimal(0)
    )
    for cap in (Decimal(0), Decimal("0.2")):
        config = RiskConfig(
            CONFIG.single_name_cap,
            CONFIG.sector_cap,
            cap,
            CONFIG.cash_floor,
            CONFIG.gross_cap,
            CONFIG.quantum,
        )
        with pytest.raises(RiskInfeasibleError) as caught:
            run_risk_engine(request(unsafe), config, RiskBudgets((), ()))
        assert "SINGLE_NAME_CAP" in caught.value.reasons


def test_current_sector_excess_fails_and_sufficient_turnover_recovers() -> None:
    unsafe = PortfolioWeights(
        tuple(PortfolioWeight(sid, Decimal("0.4")) for sid in IDS),
        Decimal("0.2"),
        Decimal(0),
    )
    with pytest.raises(RiskInfeasibleError) as caught:
        run_risk_engine(
            request(unsafe),
            RiskConfig(
                CONFIG.single_name_cap,
                CONFIG.sector_cap,
                Decimal("0.1"),
                CONFIG.cash_floor,
                CONFIG.gross_cap,
                CONFIG.quantum,
            ),
            RiskBudgets((), ()),
        )
    assert "SECTOR_CAP" in caught.value.reasons
    decision = run_risk_engine(request(unsafe), CONFIG, RiskBudgets((), ()))
    assert approved_rebalance_intent("safe", decision).targets
    assert max(row.weight for row in decision.output.weights) <= CONFIG.single_name_cap
