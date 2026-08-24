from datetime import date
from decimal import Decimal

import pytest

from stock_quant.backtest import (
    calculate_trading_costs,
    OrderSide,
    TradingCostRule,
    TradingCostSchedule,
)


def schedule() -> TradingCostSchedule:
    return TradingCostSchedule(
        "costs-v1",
        [
            TradingCostRule(
                date(2020, 1, 1), date(2023, 8, 28), Decimal("0.0003"),
                Decimal("5"), Decimal("0.00001"), Decimal("0.00001"),
                Decimal("0.001")
            ),
            TradingCostRule(
                date(2023, 8, 28), None, Decimal("0.0003"), Decimal("5"),
                Decimal("0.00001"), Decimal("0.00001"), Decimal("0.0005")
            ),
        ],
    )


def test_buy_sell_minimum_and_component_rounding() -> None:
    buy = calculate_trading_costs(
        schedule(), date(2024, 1, 2), OrderSide.BUY,
        quantity=100, price=Decimal("10.005")
    )
    sell = calculate_trading_costs(
        schedule(), date(2024, 1, 2), OrderSide.SELL,
        quantity=100, price=Decimal("10.005")
    )

    assert buy.commission == Decimal("5.00")
    assert buy.transfer_fee == Decimal("0.01")
    assert buy.stamp_duty == Decimal("0.00")
    assert buy.total == Decimal("5.01")
    assert sell.stamp_duty == Decimal("0.50")
    assert sell.total == Decimal("5.51")


def test_stamp_duty_date_change_is_half_open() -> None:
    old = calculate_trading_costs(
        schedule(), date(2023, 8, 27), OrderSide.SELL,
        quantity=1000, price=Decimal("10")
    )
    new = calculate_trading_costs(
        schedule(), date(2023, 8, 28), OrderSide.SELL,
        quantity=1000, price=Decimal("10")
    )

    assert old.stamp_duty == Decimal("10.00")
    assert new.stamp_duty == Decimal("5.00")


def test_zero_and_invalid_cases() -> None:
    zero = calculate_trading_costs(
        schedule(), date(1900, 1, 1), OrderSide.BUY,
        quantity=0, price=Decimal(0)
    )
    assert zero.total == 0
    with pytest.raises(ValueError, match="positive price"):
        calculate_trading_costs(
            schedule(), date(2024, 1, 2), OrderSide.BUY,
            quantity=1, price=Decimal(0)
        )
    with pytest.raises(ValueError, match="nonnegative"):
        calculate_trading_costs(
            schedule(), date(2024, 1, 2), OrderSide.BUY,
            quantity=-1, price=Decimal("10")
        )
