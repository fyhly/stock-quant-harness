from decimal import Decimal

import pytest

from stock_quant.domain import Exchange, SecurityId
from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.risk import apply_single_name_limit, RiskContractError


IDS = tuple(SecurityId(code, Exchange.SHANGHAI) for code in ("600000", "600001"))


def test_cap_boundary_extreme_order_and_cash_residual() -> None:
    source = PortfolioWeights(
        (
            PortfolioWeight(IDS[0], Decimal("0.8")),
            PortfolioWeight(IDS[1], Decimal("0.2")),
        ),
        Decimal(0),
        Decimal(0),
    )
    output, adjustments = apply_single_name_limit(source, Decimal("0.2"))
    assert tuple(row.weight for row in output.weights) == (
        Decimal("0.2"),
        Decimal("0.2"),
    )
    assert output.cash_weight == Decimal("0.6")
    assert len(adjustments) == 1 and adjustments[0].security_id == IDS[0]
    assert apply_single_name_limit(output, Decimal("0.2"))[0] == output


def test_invalid_cap_fails_closed() -> None:
    with pytest.raises(RiskContractError, match="cap"):
        apply_single_name_limit(
            PortfolioWeights((), Decimal(1), Decimal(0)), Decimal("1.1")
        )
