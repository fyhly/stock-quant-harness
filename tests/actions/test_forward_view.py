from datetime import date
from decimal import Decimal

import pytest

from stock_quant.actions import (
    AdjustmentFactorSeries,
    build_adjustment_factors,
    CashDividend,
    forward_adjusted_view,
    ResearchPriceExecutionError,
)
from stock_quant.data import DailyBar, DailyBarSeries
from stock_quant.domain import Exchange, SecurityId, TradingDay


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
EX = date(2024, 5, 9)


def raw_series(include_future: bool = False) -> DailyBarSeries:
    values = [
        (date(2024, 5, 8), Decimal("10")),
        (EX, Decimal("9")),
    ]
    if include_future:
        values.append((date(2024, 5, 10), Decimal("9.1")))
    return DailyBarSeries(
        SECURITY,
        [
            DailyBar(
                SECURITY,
                TradingDay(day),
                price,
                price,
                price,
                price,
                100,
                Decimal("1000"),
            )
            for day, price in values
        ],
    )


def factors() -> AdjustmentFactorSeries:
    event = CashDividend(
        SECURITY,
        date(2024, 1, 1),
        date(2024, 5, 8),
        EX,
        date(2024, 5, 15),
        Decimal("1"),
        "a" * 64,
        "v1",
    )
    return build_adjustment_factors(
        SECURITY,
        [event],
        reference_prices={EX: Decimal("10")},
        knowledge_cutoff=EX,
        version="v1",
    )


def test_forward_formula_boundary_continuity_and_lineage() -> None:
    view = forward_adjusted_view(raw_series(), factors())

    assert view.bars[0].close == Decimal("9")
    assert view.bars[1].close == Decimal("9")
    assert view.bars[0].factor == Decimal("0.9")
    assert view.bars[1].factor == Decimal(1)
    assert view.bars[0].raw_volume == 100
    assert view.bars[0].raw_amount == Decimal("1000")
    assert view.event_lineage == factors().event_lineage


def test_forward_view_is_explicitly_research_only() -> None:
    bar = forward_adjusted_view(raw_series(), factors()).bars[0]

    assert bar.research_only
    with pytest.raises(ResearchPriceExecutionError):
        bar.as_execution_price()


def test_raw_bars_after_knowledge_cutoff_are_rejected() -> None:
    with pytest.raises(ValueError, match="knowledge_cutoff"):
        forward_adjusted_view(raw_series(include_future=True), factors())


def test_security_identity_mismatch_is_rejected() -> None:
    other = DailyBarSeries(
        SecurityId("000001", Exchange.SHENZHEN),
        [],
    )
    with pytest.raises(ValueError, match="identities"):
        forward_adjusted_view(other, factors())
