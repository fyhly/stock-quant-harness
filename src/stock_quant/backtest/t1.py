"""A-share T+1 sellability derived only from an injected trading calendar."""

from dataclasses import replace
from decimal import Decimal

from stock_quant.backtest.account import Position, PositionLot
from stock_quant.domain import CalendarBoundaryError, TradingCalendar, TradingDay


class T1SellabilityError(ValueError):
    pass


def sellable_quantity(
    position: Position, on_day: TradingDay, calendar: TradingCalendar
) -> int:
    """Return quantity whose next supplied trading day has been reached."""

    if not isinstance(position, Position):
        raise TypeError("position must be a Position")
    if not isinstance(on_day, TradingDay):
        raise TypeError("on_day must be a TradingDay")
    total = 0
    for lot in position.lots:
        try:
            release = calendar.next_trading_day(lot.acquisition_day.value)
        except CalendarBoundaryError:
            continue
        if on_day >= release:
            total += lot.quantity
    return total


def require_sellable(
    position: Position,
    quantity: int,
    on_day: TradingDay,
    calendar: TradingCalendar,
) -> None:
    if type(quantity) is not int or quantity <= 0:
        raise ValueError("sell quantity must be a positive integer")
    available = sellable_quantity(position, on_day, calendar)
    if quantity > available:
        raise T1SellabilityError(
            f"requested {quantity} shares but only {available} are T+1 sellable"
        )


def credit_corporate_action_lot(
    position: Position,
    credit_day: TradingDay,
    quantity: int,
    *,
    unit_cost: Decimal = Decimal(0),
) -> Position:
    """Add credited shares as a new lot frozen until the next trading day."""

    if type(quantity) is not int or quantity <= 0:
        raise ValueError("credited quantity must be a positive integer")
    lot = PositionLot(credit_day, quantity, unit_cost)
    return replace(position, lots=position.lots + (lot,))
