from decimal import Decimal

import pytest

from stock_quant.domain import Exchange, SecurityId
from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.risk import apply_cash_exposure_limits, RiskContractError


SECURITY = SecurityId("600000", Exchange.SHANGHAI)


def test_cash_floor_gross_empty_and_extreme_scaling() -> None:
    source = PortfolioWeights(
        (PortfolioWeight(SECURITY, Decimal(1)),), Decimal(0), Decimal(0)
    )
    output, adjustments = apply_cash_exposure_limits(
        source, cash_floor=Decimal("0.3"), gross_cap=Decimal("0.8")
    )
    assert output.weights[0].weight == Decimal("0.7")
    assert output.cash_weight == Decimal("0.3") and len(adjustments) == 1
    empty = apply_cash_exposure_limits(
        PortfolioWeights((), Decimal(1), Decimal(0)),
        cash_floor=Decimal(1),
        gross_cap=Decimal(0),
    )[0]
    assert empty.cash_weight == 1 and empty.weights == ()


def test_overallocation_and_invalid_configuration_fail_closed() -> None:
    with pytest.raises(RiskContractError, match="over-allocated"):
        apply_cash_exposure_limits(
            PortfolioWeights(
                (PortfolioWeight(SECURITY, Decimal(1)),), Decimal("0.1"), Decimal(0)
            ),
            cash_floor=Decimal(0),
            gross_cap=Decimal(1),
        )
    with pytest.raises(RiskContractError, match="gross"):
        apply_cash_exposure_limits(
            PortfolioWeights((), Decimal(1), Decimal(0)),
            cash_floor=Decimal(0),
            gross_cap=Decimal("1.1"),
        )
