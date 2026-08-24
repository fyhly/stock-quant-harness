from decimal import Decimal

import pytest

from stock_quant.domain import Exchange, SecurityId
from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.risk import apply_turnover_limit, RiskContractError


IDS = (SecurityId("600000", Exchange.SHANGHAI), SecurityId("600001", Exchange.SHANGHAI))
CURRENT = PortfolioWeights(
    (PortfolioWeight(IDS[0], Decimal("0.4")),), Decimal("0.6"), Decimal(0)
)
PROPOSED = PortfolioWeights(
    (PortfolioWeight(IDS[1], Decimal("0.8")),), Decimal("0.2"), Decimal(0)
)


def test_zero_full_partial_cap_buy_sell_cash_formula() -> None:
    zero = apply_turnover_limit(PROPOSED, CURRENT, Decimal(0))
    full = apply_turnover_limit(PROPOSED, CURRENT, Decimal(1))
    partial = apply_turnover_limit(PROPOSED, CURRENT, Decimal("0.4"))
    assert zero.portfolio == CURRENT and zero.achieved_turnover == 0
    assert full.portfolio == PROPOSED and full.requested_turnover == Decimal("0.8")
    assert partial.achieved_turnover == Decimal("0.4")
    assert partial.portfolio.cash_weight == Decimal("0.4")


def test_deterministic_extreme_and_invalid_cap() -> None:
    assert apply_turnover_limit(
        PROPOSED, CURRENT, Decimal("0.2")
    ) == apply_turnover_limit(PROPOSED, CURRENT, Decimal("0.2"))
    with pytest.raises(RiskContractError, match="turnover"):
        apply_turnover_limit(PROPOSED, CURRENT, Decimal("1.1"))
