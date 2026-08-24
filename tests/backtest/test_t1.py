from datetime import date, time
from decimal import Decimal

import pytest

from stock_quant.backtest import (
    credit_corporate_action_lot,
    Position,
    PositionLot,
    require_sellable,
    sellable_quantity,
    T1SellabilityError,
)
from stock_quant.domain import Exchange, SecurityId, TradingCalendar, TradingDay, TradingSession


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
D1 = TradingDay(date(2024, 1, 5))  # Friday
D2 = TradingDay(date(2024, 1, 8))  # Monday
D3 = TradingDay(date(2024, 1, 9))


def calendar() -> TradingCalendar:
    session = TradingSession("day", time(9, 30), time(15))
    return TradingCalendar(
        {D1: (session,), D2: (session,), D3: (session,)},
        coverage_start=date(2024, 1, 5),
        coverage_end=date(2024, 1, 9),
        timezone="Asia/Shanghai",
    )


def test_same_day_frozen_and_next_supplied_day_released_across_weekend() -> None:
    position = Position(SECURITY, (PositionLot(D1, 100, Decimal("10")),))

    assert sellable_quantity(position, D1, calendar()) == 0
    assert sellable_quantity(position, D2, calendar()) == 100
    with pytest.raises(T1SellabilityError):
        require_sellable(position, 1, D1, calendar())


def test_partial_lots_release_independently() -> None:
    position = Position(
        SECURITY,
        (PositionLot(D1, 100, Decimal("10")), PositionLot(D2, 200, Decimal("11"))),
    )

    assert sellable_quantity(position, D2, calendar()) == 100
    assert sellable_quantity(position, D3, calendar()) == 300
    require_sellable(position, 100, D2, calendar())
    with pytest.raises(T1SellabilityError):
        require_sellable(position, 101, D2, calendar())


def test_corporate_action_credit_is_frozen_on_credit_day() -> None:
    original = Position(SECURITY, (PositionLot(D1, 100, Decimal("10")),))
    credited = credit_corporate_action_lot(original, D2, 30)

    assert credited.quantity == 130
    assert sellable_quantity(credited, D2, calendar()) == 100
    assert sellable_quantity(credited, D3, calendar()) == 130
