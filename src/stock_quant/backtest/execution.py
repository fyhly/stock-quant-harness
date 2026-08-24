"""Deterministic next-open raw fills with slippage, volume, cash, and lots."""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_FLOOR
from typing import Optional

from stock_quant.actions import RawExecutionBar, RawExecutionPriceView
from stock_quant.backtest.account import AccountState, book_buy, book_sell
from stock_quant.backtest.constraints import (
    OrderSide,
    RejectionCode,
    SuspensionConstraint,
)
from stock_quant.backtest.costs import (
    calculate_trading_costs,
    TradingCostBreakdown,
    TradingCostSchedule,
)
from stock_quant.backtest.limits import (
    evaluate_price_limit,
    fill_price_within_limits,
    PriceLimitSchedule,
)
from stock_quant.backtest.t1 import sellable_quantity
from stock_quant.domain import SecurityId, STStatus, TradingCalendar, TradingDay


@dataclass(frozen=True)
class OrderIntent:
    order_id: str
    security_id: SecurityId
    side: OrderSide
    quantity: int
    decision_day: TradingDay
    fill_day: TradingDay

    def __post_init__(self) -> None:
        if type(self.quantity) is not int or self.quantity <= 0:
            raise ValueError("order quantity must be a positive integer")


@dataclass(frozen=True)
class SlippageModel:
    version: str
    basis_points: Decimal

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("slippage version must be non-empty")
        if (
            not isinstance(self.basis_points, Decimal)
            or not self.basis_points.is_finite()
            or self.basis_points < 0
        ):
            raise ValueError("basis_points must be a nonnegative finite Decimal")


@dataclass(frozen=True)
class Fill:
    order_id: str
    security_id: SecurityId
    side: OrderSide
    trading_day: TradingDay
    quantity: int
    raw_open: Decimal
    price: Decimal
    costs: TradingCostBreakdown
    slippage_version: str


@dataclass(frozen=True)
class ExecutionOutcome:
    account: AccountState
    fill: Optional[Fill]
    rejection: Optional[RejectionCode]


def execute_next_open(
    order: OrderIntent,
    *,
    view: RawExecutionPriceView,
    account: AccountState,
    calendar: TradingCalendar,
    suspension: SuspensionConstraint,
    price_limits: PriceLimitSchedule,
    prior_close: Optional[Decimal],
    st_status: Optional[STStatus],
    costs: TradingCostSchedule,
    slippage: SlippageModel,
    participation_cap: Decimal,
) -> ExecutionOutcome:
    if not isinstance(view, RawExecutionPriceView):
        raise TypeError("fills require RawExecutionPriceView")
    if (
        not isinstance(participation_cap, Decimal)
        or not Decimal(0) < participation_cap <= Decimal(1)
    ):
        raise ValueError("participation_cap must be a Decimal in (0, 1]")
    try:
        expected = calendar.next_trading_day(order.decision_day.value)
    except ValueError:
        return _reject(account, RejectionCode.INVALID_FILL_TIMING)
    if order.fill_day != expected:
        return _reject(account, RejectionCode.INVALID_FILL_TIMING)
    bar = _bar_on(view, order)
    if bar is None:
        return _reject(account, RejectionCode.MISSING_RAW_BAR)
    status = suspension.evaluate(order.security_id, order.fill_day, order.side)
    if not status.allowed:
        assert status.rejection is not None
        return _reject(account, status.rejection)
    limit_decision, band = evaluate_price_limit(
        price_limits,
        bar,
        prior_close=prior_close,
        st_status=st_status,
        side=order.side,
    )
    if not limit_decision.allowed or band is None:
        assert limit_decision.rejection is not None
        return _reject(account, limit_decision.rejection)
    price = _slipped_price(bar, order.side, slippage.basis_points)
    if not fill_price_within_limits(price, bar, band):
        return _reject(account, RejectionCode.PRICE_LIMIT)
    volume_cap = int(
        (Decimal(bar.volume) * participation_cap).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    if volume_cap == 0:
        return _reject(account, RejectionCode.ZERO_VOLUME)
    position = account.position(order.security_id)
    candidate = min(order.quantity, volume_cap)
    if order.side is OrderSide.BUY:
        quantity = (candidate // 100) * 100
        while quantity > 0:
            fee = calculate_trading_costs(
                costs, order.fill_day.value, order.side, quantity=quantity, price=price
            )
            if fee.notional + fee.total <= account.cash:
                break
            quantity -= 100
        if quantity == 0:
            return _reject(account, RejectionCode.INSUFFICIENT_CASH)
        fee = calculate_trading_costs(
            costs, order.fill_day.value, order.side, quantity=quantity, price=price
        )
        updated = book_buy(
            account, order.security_id, order.fill_day, quantity=quantity, price=price
        )
        updated = replace(updated, cash=updated.cash - fee.total)
    else:
        available = sellable_quantity(position, order.fill_day, calendar)
        candidate = min(candidate, available, position.quantity)
        full_odd_lot = candidate == position.quantity and order.quantity >= position.quantity
        quantity = candidate if full_odd_lot else (candidate // 100) * 100
        if quantity == 0:
            return _reject(account, RejectionCode.INSUFFICIENT_QUANTITY)
        fee = calculate_trading_costs(
            costs, order.fill_day.value, order.side, quantity=quantity, price=price
        )
        updated = book_sell(
            account, order.security_id, order.fill_day, quantity=quantity, price=price
        )
        updated = replace(updated, cash=updated.cash - fee.total)
    fill = Fill(
        order.order_id,
        order.security_id,
        order.side,
        order.fill_day,
        quantity,
        bar.open,
        price,
        fee,
        slippage.version,
    )
    return ExecutionOutcome(updated, fill, None)


def _bar_on(view: RawExecutionPriceView, order: OrderIntent) -> Optional[RawExecutionBar]:
    if view.security_id != order.security_id:
        return None
    for bar in view.bars:
        if bar.trading_day == order.fill_day:
            return bar
    return None


def _slipped_price(
    bar: RawExecutionBar, side: OrderSide, basis_points: Decimal
) -> Decimal:
    direction = Decimal(1) if side is OrderSide.BUY else Decimal(-1)
    proposed = bar.open * (Decimal(1) + direction * basis_points / Decimal(10000))
    return min(max(proposed, bar.low), bar.high)


def _reject(account: AccountState, code: RejectionCode) -> ExecutionOutcome:
    return ExecutionOutcome(account, None, code)
