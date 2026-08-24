from decimal import Decimal

import pytest

from stock_quant.domain import Exchange, SecurityId
from stock_quant.portfolio import equal_weight, PortfolioConstructionError


IDS = tuple(
    SecurityId(code, Exchange.SHANGHAI) for code in ("600000", "600001", "600002")
)


def test_exact_sum_cash_rounding_and_order() -> None:
    first = equal_weight(reversed(IDS), cash_target=Decimal(0), quantum=Decimal("0.01"))
    second = equal_weight(IDS, cash_target=Decimal(0), quantum=Decimal("0.01"))
    assert first == second
    assert (
        sum((row.weight for row in first.weights), Decimal(0)) + first.cash_weight == 1
    )
    assert first.rounding_residual == Decimal("0.01")


def test_empty_selection_and_invalid_selection() -> None:
    empty = equal_weight((), cash_target=Decimal("0.2"), quantum=Decimal("0.01"))
    assert empty.weights == () and empty.cash_weight == 1
    assert empty.rounding_residual == Decimal("0.8")
    with pytest.raises(PortfolioConstructionError, match="unique"):
        equal_weight((IDS[0], IDS[0]), cash_target=Decimal(0), quantum=Decimal("0.01"))
