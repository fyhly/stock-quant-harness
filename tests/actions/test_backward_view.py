from datetime import date
from decimal import Decimal

import pytest

from stock_quant.actions import (
    AdjustmentFactorSeries,
    backward_adjusted_view,
    build_adjustment_factors,
    CashDividend,
    ResearchPriceExecutionError,
)
from stock_quant.data import DailyBar, DailyBarSeries
from stock_quant.domain import Exchange, SecurityId, TradingDay


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
EX = date(2024, 5, 9)


def raw_series() -> DailyBarSeries:
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
            for day, price in (
                (date(2024, 5, 8), Decimal("10")),
                (EX, Decimal("9")),
            )
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


def test_backward_formula_base_boundary_continuity_and_lineage() -> None:
    view = backward_adjusted_view(raw_series(), factors(), base_date=EX)

    assert view.bars[0].close == Decimal("10")
    assert view.bars[1].close == Decimal("10")
    assert view.bars[0].factor == Decimal(1)
    assert view.bars[1].factor == Decimal(1) / Decimal("0.9")
    assert view.base_date == EX
    assert view.event_lineage == factors().event_lineage


def test_backward_view_is_research_only() -> None:
    bar = backward_adjusted_view(raw_series(), factors(), base_date=EX).bars[1]

    assert bar.research_only
    with pytest.raises(ResearchPriceExecutionError):
        bar.as_execution_price()


def test_base_date_must_match_factor_cutoff() -> None:
    with pytest.raises(ValueError, match="base_date"):
        backward_adjusted_view(
            raw_series(), factors(), base_date=date(2024, 5, 8)
        )
