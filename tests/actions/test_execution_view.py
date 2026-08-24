from datetime import date
from decimal import Decimal

import pytest

from stock_quant.actions import (
    build_adjustment_factors,
    CashDividend,
    execution_price,
    ExecutionPriceField,
    forward_adjusted_view,
    raw_execution_price_view,
)
from stock_quant.data import DailyBar, DailyBarSeries
from stock_quant.domain import Exchange, SecurityId, TradingDay


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
DAY = TradingDay(date(2024, 5, 8))
EX = date(2024, 5, 9)


def raw() -> DailyBarSeries:
    return DailyBarSeries(
        SECURITY,
        [
            DailyBar(
                SECURITY,
                DAY,
                Decimal("10"),
                Decimal("11"),
                Decimal("9"),
                Decimal("10.5"),
                100,
                Decimal("1050"),
            )
        ],
    )


def test_raw_ohlc_is_unchanged_and_typed() -> None:
    view = raw_execution_price_view(raw())

    assert execution_price(view, DAY, ExecutionPriceField.OPEN) == Decimal("10")
    assert execution_price(view, DAY, ExecutionPriceField.HIGH) == Decimal("11")
    assert execution_price(view, DAY, ExecutionPriceField.LOW) == Decimal("9")
    assert execution_price(view, DAY, ExecutionPriceField.CLOSE) == Decimal("10.5")
    assert view.bars[0].source_schema_version == "daily-bar-v1"


def test_research_view_cannot_enter_execution_api() -> None:
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
    factors = build_adjustment_factors(
        SECURITY,
        [event],
        reference_prices={EX: Decimal("10")},
        knowledge_cutoff=EX,
        version="v1",
    )
    adjusted = forward_adjusted_view(raw(), factors)

    with pytest.raises(TypeError, match="only RawExecutionPriceView"):
        execution_price(
            adjusted,  # type: ignore[arg-type]
            DAY,
            ExecutionPriceField.CLOSE,
        )


def test_action_factors_never_mutate_raw_execution_view() -> None:
    before = raw_execution_price_view(raw())
    _ = build_adjustment_factors(
        SECURITY,
        [
            CashDividend(
                SECURITY,
                date(2024, 1, 1),
                date(2024, 5, 8),
                EX,
                date(2024, 5, 15),
                Decimal("1"),
                "a" * 64,
                "v1",
            )
        ],
        reference_prices={EX: Decimal("10")},
        knowledge_cutoff=EX,
        version="v1",
    )
    after = raw_execution_price_view(raw())

    assert before == after
