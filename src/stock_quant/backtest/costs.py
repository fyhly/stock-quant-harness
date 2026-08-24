"""Versioned exact trading fees with per-component RMB-cent rounding."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional, Tuple

from stock_quant.backtest.constraints import OrderSide


_CENT = Decimal("0.01")


@dataclass(frozen=True)
class TradingCostRule:
    effective_from: date
    effective_to: Optional[date]
    commission_rate: Decimal
    minimum_commission: Decimal
    buy_transfer_rate: Decimal
    sell_transfer_rate: Decimal
    sell_stamp_duty_rate: Decimal

    def __post_init__(self) -> None:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be after effective_from")
        for name in (
            "commission_rate",
            "minimum_commission",
            "buy_transfer_rate",
            "sell_transfer_rate",
            "sell_stamp_duty_rate",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise ValueError(f"{name} must be a nonnegative finite Decimal")

    def covers(self, on_date: date) -> bool:
        return self.effective_from <= on_date and (
            self.effective_to is None or on_date < self.effective_to
        )


class TradingCostSchedule:
    def __init__(self, version: str, rules: Iterable[TradingCostRule]) -> None:
        if not version.strip():
            raise ValueError("cost schedule version must be non-empty")
        ordered = tuple(sorted(rules, key=lambda rule: rule.effective_from))
        for previous, current in zip(ordered, ordered[1:]):
            if previous.effective_to is None or previous.effective_to > current.effective_from:
                raise ValueError("cost schedule rules cannot overlap")
        self.version = version
        self.rules: Tuple[TradingCostRule, ...] = ordered

    def rule_on(self, on_date: date) -> TradingCostRule:
        matches = tuple(rule for rule in self.rules if rule.covers(on_date))
        if len(matches) != 1:
            raise ValueError("missing or ambiguous trading-cost rule")
        return matches[0]


@dataclass(frozen=True)
class TradingCostBreakdown:
    notional: Decimal
    commission: Decimal
    transfer_fee: Decimal
    stamp_duty: Decimal
    total: Decimal
    rule_version: str


def calculate_trading_costs(
    schedule: TradingCostSchedule,
    on_date: date,
    side: OrderSide,
    *,
    quantity: int,
    price: Decimal,
) -> TradingCostBreakdown:
    if type(quantity) is not int or quantity < 0:
        raise ValueError("quantity must be a nonnegative integer")
    if not isinstance(price, Decimal) or not price.is_finite() or price < 0:
        raise ValueError("price must be a nonnegative finite Decimal")
    if not isinstance(side, OrderSide):
        raise TypeError("side must be OrderSide")
    if quantity == 0:
        return TradingCostBreakdown(
            Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), schedule.version
        )
    if price == 0:
        raise ValueError("positive quantity requires positive price")
    rule = schedule.rule_on(on_date)
    notional = Decimal(quantity) * price
    commission = _round_cent(
        max(notional * rule.commission_rate, rule.minimum_commission)
    )
    transfer_rate = (
        rule.buy_transfer_rate if side is OrderSide.BUY else rule.sell_transfer_rate
    )
    transfer = _round_cent(notional * transfer_rate)
    stamp = _round_cent(
        notional * rule.sell_stamp_duty_rate
        if side is OrderSide.SELL
        else Decimal(0)
    )
    return TradingCostBreakdown(
        notional,
        commission,
        transfer,
        stamp,
        commission + transfer + stamp,
        schedule.version,
    )


def _round_cent(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)
