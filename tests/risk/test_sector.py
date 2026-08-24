from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from stock_quant.domain import Exchange, SecurityId, TradingDay
from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.risk import apply_sector_limit, PITClassification, RiskContractError


IDS = tuple(
    SecurityId(code, Exchange.SHANGHAI) for code in ("600000", "600001", "600002")
)
DAY = TradingDay(date(2024, 1, 2))
PORTFOLIO = PortfolioWeights(
    tuple(PortfolioWeight(sid, Decimal("0.3")) for sid in IDS),
    Decimal("0.1"),
    Decimal(0),
)
FACTS = tuple(
    PITClassification(sid, DAY, "BANK" if index < 2 else "TECH", "a" * 64)
    for index, sid in enumerate(IDS)
)


def test_sector_excess_multiple_names_ties_and_pit_change() -> None:
    output, adjustments = apply_sector_limit(
        PORTFOLIO,
        reversed(FACTS),
        as_of=DAY,
        cap=Decimal("0.4"),
        quantum=Decimal("0.0001"),
    )
    assert tuple(row.weight for row in output.weights) == (
        Decimal("0.2"),
        Decimal("0.2"),
        Decimal("0.3"),
    )
    assert len(adjustments) == 2 and output.cash_weight == Decimal("0.3")
    changed = tuple(
        replace(row, industry_code=f"S{index}") for index, row in enumerate(FACTS)
    )
    assert (
        apply_sector_limit(
            PORTFOLIO, changed, as_of=DAY, cap=Decimal("0.4"), quantum=Decimal("0.0001")
        )[0]
        == PORTFOLIO
    )


def test_missing_gap_and_current_classification_leak_fail() -> None:
    with pytest.raises(RiskContractError, match="missing"):
        apply_sector_limit(
            PORTFOLIO,
            FACTS[:-1],
            as_of=DAY,
            cap=Decimal("0.4"),
            quantum=Decimal("0.01"),
        )
    future = tuple(replace(row, as_of=TradingDay(date(2024, 2, 1))) for row in FACTS)
    with pytest.raises(RiskContractError, match="as-of"):
        apply_sector_limit(
            PORTFOLIO, future, as_of=DAY, cap=Decimal("0.4"), quantum=Decimal("0.01")
        )
