"""Typed target weights converted to deterministic next-day order intents."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from typing import Iterable, Mapping, Tuple

from stock_quant.backtest.account import AccountState, RawMark, value_account
from stock_quant.backtest.constraints import OrderSide
from stock_quant.backtest.execution import OrderIntent
from stock_quant.domain import SecurityId, TradingCalendar, TradingDay


@dataclass(frozen=True, order=True)
class TargetWeight:
    security_id: SecurityId
    weight: Decimal

    def __post_init__(self) -> None:
        if (
            not isinstance(self.weight, Decimal)
            or not self.weight.is_finite()
            or not Decimal(0) <= self.weight <= Decimal(1)
        ):
            raise ValueError("target weight must be a finite Decimal in [0, 1]")


@dataclass(frozen=True)
class RebalanceIntent:
    intent_id: str
    decision_day: TradingDay
    targets: Tuple[TargetWeight, ...]

    def __post_init__(self) -> None:
        ids = tuple(target.security_id for target in self.targets)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("targets must be sorted and unique")
        if sum((target.weight for target in self.targets), Decimal(0)) > Decimal(1):
            raise ValueError("target weights cannot sum above one")


@dataclass(frozen=True)
class RebalancePlan:
    intent_id: str
    pre_trade_equity: Decimal
    target_quantities: Tuple[Tuple[SecurityId, int], ...]
    orders: Tuple[OrderIntent, ...]
    residual_cash: Decimal


def create_rebalance_intent(
    intent_id: str,
    decision_day: TradingDay,
    targets: Iterable[TargetWeight],
) -> RebalanceIntent:
    return RebalanceIntent(intent_id, decision_day, tuple(sorted(targets)))


def plan_rebalance(
    intent: RebalanceIntent,
    *,
    account: AccountState,
    marks: Mapping[SecurityId, RawMark],
    calendar: TradingCalendar,
) -> RebalancePlan:
    """Plan orders only; execution remains exclusively in the fill layer."""

    if not isinstance(intent, RebalanceIntent):
        raise TypeError("intent must be RebalanceIntent")
    equity = value_account(account, intent.decision_day, marks).equity
    fill_day = calendar.next_trading_day(intent.decision_day.value)
    weights = {target.security_id: target.weight for target in intent.targets}
    securities = tuple(
        sorted(set(weights) | {position.security_id for position in account.positions})
    )
    targets = []
    orders = []
    target_market_value = Decimal(0)
    for security_id in securities:
        mark = marks.get(security_id)
        if mark is None or mark.trading_day != intent.decision_day:
            raise ValueError(f"missing decision-day raw mark for {security_id}")
        target_value = equity * weights.get(security_id, Decimal(0))
        lots = int(
            (target_value / mark.price / Decimal(100)).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )
        target_quantity = lots * 100
        targets.append((security_id, target_quantity))
        target_market_value += Decimal(target_quantity) * mark.price
        current = account.position(security_id).quantity
        delta = target_quantity - current
        if delta:
            side = OrderSide.BUY if delta > 0 else OrderSide.SELL
            orders.append(
                OrderIntent(
                    f"{intent.intent_id}:{side.value}:{security_id}",
                    security_id,
                    side,
                    abs(delta),
                    intent.decision_day,
                    fill_day,
                )
            )
    ordered = tuple(
        sorted(
            orders,
            key=lambda order: (
                0 if order.side is OrderSide.SELL else 1,
                order.security_id,
            ),
        )
    )
    return RebalancePlan(
        intent.intent_id,
        equity,
        tuple(targets),
        ordered,
        equity - target_market_value,
    )
