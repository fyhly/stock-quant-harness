"""Exact immutable cash, lot, position, and raw-mark valuation accounting."""

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Dict, Mapping, Tuple

from stock_quant.domain import SecurityId, TradingDay


class AccountError(ValueError):
    pass


class MissingValuationError(AccountError):
    pass


class StaleValuationError(AccountError):
    pass


@dataclass(frozen=True)
class PositionLot:
    acquisition_day: TradingDay
    quantity: int
    unit_cost: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.acquisition_day, TradingDay):
            raise TypeError("acquisition_day must be TradingDay")
        if type(self.quantity) is not int or self.quantity <= 0:
            raise ValueError("lot quantity must be a positive integer")
        if (
            not isinstance(self.unit_cost, Decimal)
            or not self.unit_cost.is_finite()
            or self.unit_cost < 0
        ):
            raise ValueError("unit_cost must be a nonnegative finite Decimal")


@dataclass(frozen=True)
class Position:
    security_id: SecurityId
    lots: Tuple[PositionLot, ...]

    @property
    def quantity(self) -> int:
        return sum(lot.quantity for lot in self.lots)

    @property
    def total_cost(self) -> Decimal:
        return sum(
            (Decimal(lot.quantity) * lot.unit_cost for lot in self.lots), Decimal(0)
        )


@dataclass(frozen=True)
class TradeAccountingEntry:
    security_id: SecurityId
    trading_day: TradingDay
    side: str
    quantity: int
    price: Decimal
    cash_delta: Decimal
    cost_basis_delta: Decimal
    realized_pnl: Decimal


@dataclass(frozen=True)
class AccountState:
    cash: Decimal
    positions: Tuple[Position, ...] = ()
    ledger: Tuple[TradeAccountingEntry, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.cash, Decimal) or not self.cash.is_finite() or self.cash < 0:
            raise ValueError("cash must be a nonnegative finite Decimal")
        ids = tuple(position.security_id for position in self.positions)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("positions must be sorted and unique by security")

    def position(self, security_id: SecurityId) -> Position:
        for position in self.positions:
            if position.security_id == security_id:
                return position
        return Position(security_id, ())


@dataclass(frozen=True)
class RawMark:
    security_id: SecurityId
    trading_day: TradingDay
    price: Decimal

    def __post_init__(self) -> None:
        if (
            not isinstance(self.price, Decimal)
            or not self.price.is_finite()
            or self.price <= 0
        ):
            raise ValueError("raw mark price must be a positive finite Decimal")


@dataclass(frozen=True)
class AccountValuation:
    trading_day: TradingDay
    cash: Decimal
    market_value: Decimal
    equity: Decimal
    position_values: Tuple[Tuple[SecurityId, Decimal], ...]


def book_buy(
    state: AccountState,
    security_id: SecurityId,
    trading_day: TradingDay,
    *,
    quantity: int,
    price: Decimal,
) -> AccountState:
    _validate_trade(quantity, price)
    required = Decimal(quantity) * price
    if required > state.cash:
        raise AccountError("insufficient cash")
    existing = state.position(security_id)
    position = Position(
        security_id, existing.lots + (PositionLot(trading_day, quantity, price),)
    )
    entry = TradeAccountingEntry(
        security_id, trading_day, "BUY", quantity, price, -required, required, Decimal(0)
    )
    return _replace_position(state, position, state.cash - required, entry)


def book_sell(
    state: AccountState,
    security_id: SecurityId,
    trading_day: TradingDay,
    *,
    quantity: int,
    price: Decimal,
) -> AccountState:
    _validate_trade(quantity, price)
    existing = state.position(security_id)
    if quantity > existing.quantity:
        raise AccountError("insufficient position quantity")
    remaining = quantity
    retained = []
    removed_cost = Decimal(0)
    for index, lot in enumerate(existing.lots):
        sold = min(remaining, lot.quantity)
        removed_cost += Decimal(sold) * lot.unit_cost
        remaining -= sold
        if sold < lot.quantity:
            retained.append(replace(lot, quantity=lot.quantity - sold))
        if remaining == 0:
            retained.extend(existing.lots[index + 1 :])
            break
    proceeds = Decimal(quantity) * price
    position = Position(security_id, tuple(retained))
    entry = TradeAccountingEntry(
        security_id,
        trading_day,
        "SELL",
        quantity,
        price,
        proceeds,
        -removed_cost,
        proceeds - removed_cost,
    )
    return _replace_position(state, position, state.cash + proceeds, entry)


def value_account(
    state: AccountState,
    trading_day: TradingDay,
    marks: Mapping[SecurityId, RawMark],
) -> AccountValuation:
    values = []
    for position in state.positions:
        if position.quantity == 0:
            continue
        mark = marks.get(position.security_id)
        if mark is None:
            raise MissingValuationError(f"missing raw mark for {position.security_id}")
        if mark.security_id != position.security_id:
            raise MissingValuationError("raw mark identity mismatch")
        if mark.trading_day != trading_day:
            raise StaleValuationError(f"stale raw mark for {position.security_id}")
        values.append((position.security_id, Decimal(position.quantity) * mark.price))
    frozen = tuple(values)
    market = sum((value for _, value in frozen), Decimal(0))
    return AccountValuation(trading_day, state.cash, market, state.cash + market, frozen)


def _validate_trade(quantity: int, price: Decimal) -> None:
    if type(quantity) is not int or quantity <= 0:
        raise ValueError("trade quantity must be a positive integer")
    if not isinstance(price, Decimal) or not price.is_finite() or price <= 0:
        raise ValueError("trade price must be a positive finite Decimal")


def _replace_position(
    state: AccountState,
    updated: Position,
    cash: Decimal,
    entry: TradeAccountingEntry,
) -> AccountState:
    by_id: Dict[SecurityId, Position] = {
        position.security_id: position for position in state.positions
    }
    if updated.quantity:
        by_id[updated.security_id] = updated
    else:
        by_id.pop(updated.security_id, None)
    return AccountState(cash, tuple(sorted(by_id.values(), key=lambda item: item.security_id)), state.ledger + (entry,))
