from datetime import date
from decimal import Decimal
from typing import Tuple

import pytest

from stock_quant.domain import Exchange, SecurityId, TradingDay
from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.risk import create_risk_request, PITClassification, RiskContractError


IDS = (SecurityId("600000", Exchange.SHANGHAI), SecurityId("600001", Exchange.SHANGHAI))
DAY = TradingDay(date(2024, 1, 2))
HASH = "a" * 64
PORTFOLIO = PortfolioWeights(
    tuple(PortfolioWeight(sid, Decimal("0.4")) for sid in IDS),
    Decimal("0.2"),
    Decimal(0),
)


def classifications(day: TradingDay = DAY) -> Tuple[PITClassification, ...]:
    return tuple(PITClassification(sid, day, "BANK", HASH) for sid in IDS)


def test_contract_alignment_identity_and_determinism() -> None:
    first = create_risk_request(
        DAY,
        PORTFOLIO,
        PORTFOLIO,
        reversed(classifications()),
        config_identity=HASH,
        upstream_identity=HASH,
    )
    second = create_risk_request(
        DAY,
        PORTFOLIO,
        PORTFOLIO,
        classifications(),
        config_identity=HASH,
        upstream_identity=HASH,
    )
    assert first == second


def test_misaligned_asof_missing_and_identity_fail_closed() -> None:
    with pytest.raises(RiskContractError, match="as-of"):
        create_risk_request(
            DAY,
            PORTFOLIO,
            PORTFOLIO,
            classifications(TradingDay(date(2024, 1, 3))),
            config_identity=HASH,
            upstream_identity=HASH,
        )
    with pytest.raises(RiskContractError, match="align"):
        create_risk_request(
            DAY,
            PORTFOLIO,
            PORTFOLIO,
            classifications()[:1],
            config_identity=HASH,
            upstream_identity=HASH,
        )
    with pytest.raises(RiskContractError, match="identity"):
        create_risk_request(
            DAY,
            PORTFOLIO,
            PORTFOLIO,
            classifications(),
            config_identity="bad",
            upstream_identity=HASH,
        )
