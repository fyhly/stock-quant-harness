"""Injected versioned board/date-aware A-share price-limit constraints."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional

from stock_quant.actions import RawExecutionBar
from stock_quant.backtest.constraints import (
    ConstraintDecision,
    OrderSide,
    RejectionCode,
)
from stock_quant.domain import MarketSegment, STStatus


@dataclass(frozen=True)
class PriceLimitRule:
    market_segment: MarketSegment
    effective_from: date
    effective_to: Optional[date]
    percentage: Decimal
    st_status: Optional[STStatus] = None

    def __post_init__(self) -> None:
        if type(self.effective_from) is not date:
            raise TypeError("effective_from must be a date")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be after effective_from")
        if (
            not isinstance(self.percentage, Decimal)
            or not self.percentage.is_finite()
            or not Decimal(0) < self.percentage < Decimal(1)
        ):
            raise ValueError("limit percentage must be a finite Decimal in (0, 1)")

    def covers(self, on_date: date) -> bool:
        return self.effective_from <= on_date and (
            self.effective_to is None or on_date < self.effective_to
        )


@dataclass(frozen=True)
class PriceLimitBand:
    lower: Decimal
    upper: Decimal
    percentage: Decimal
    rule_version: str


class PriceLimitSchedule:
    def __init__(
        self,
        version: str,
        rules: Iterable[PriceLimitRule],
        *,
        tick_size: Decimal = Decimal("0.01"),
    ) -> None:
        if not version.strip():
            raise ValueError("price-limit version must be non-empty")
        if tick_size != Decimal("0.01"):
            raise ValueError("Phase 5 supports explicit A-share tick_size 0.01 only")
        ordered = tuple(
            sorted(
                rules,
                key=lambda rule: (
                    rule.market_segment.value,
                    rule.st_status.value if rule.st_status else "",
                    rule.effective_from,
                ),
            )
        )
        for index, rule in enumerate(ordered):
            for other in ordered[index + 1 :]:
                if (
                    rule.market_segment == other.market_segment
                    and rule.st_status == other.st_status
                    and (rule.effective_to is None or rule.effective_to > other.effective_from)
                ):
                    raise ValueError("price-limit rules cannot overlap")
        self.version = version
        self.rules = ordered
        self.tick_size = tick_size

    def band(
        self,
        market_segment: MarketSegment,
        st_status: STStatus,
        on_date: date,
        prior_close: Decimal,
    ) -> PriceLimitBand:
        if (
            not isinstance(prior_close, Decimal)
            or not prior_close.is_finite()
            or prior_close <= 0
        ):
            raise ValueError("prior_close must be a positive finite Decimal")
        candidates = tuple(
            rule
            for rule in self.rules
            if rule.market_segment is market_segment
            and rule.covers(on_date)
            and (rule.st_status is None or rule.st_status is st_status)
        )
        specific = tuple(rule for rule in candidates if rule.st_status is st_status)
        selected = specific or tuple(rule for rule in candidates if rule.st_status is None)
        if len(selected) != 1:
            raise ValueError("missing or ambiguous price-limit rule")
        percentage = selected[0].percentage
        lower = (prior_close * (Decimal(1) - percentage)).quantize(
            self.tick_size, rounding=ROUND_HALF_UP
        )
        upper = (prior_close * (Decimal(1) + percentage)).quantize(
            self.tick_size, rounding=ROUND_HALF_UP
        )
        return PriceLimitBand(lower, upper, percentage, self.version)


def evaluate_price_limit(
    schedule: PriceLimitSchedule,
    bar: RawExecutionBar,
    *,
    prior_close: Optional[Decimal],
    st_status: Optional[STStatus],
    side: OrderSide,
) -> tuple[ConstraintDecision, Optional[PriceLimitBand]]:
    if prior_close is None or st_status is None:
        return (
            ConstraintDecision(
                False,
                RejectionCode.MISSING_PRICE_LIMIT_FACTS,
                "prior close or historical ST status is missing",
            ),
            None,
        )
    try:
        band = schedule.band(
            bar.security_id.market_segment,
            st_status,
            bar.trading_day.value,
            prior_close,
        )
    except ValueError:
        return (
            ConstraintDecision(
                False,
                RejectionCode.MISSING_PRICE_LIMIT_FACTS,
                "no unambiguous versioned limit rule covers execution date",
            ),
            None,
        )
    one_price = bar.open == bar.high == bar.low == bar.close
    blocked = one_price and (
        (side is OrderSide.BUY and bar.close == band.upper)
        or (side is OrderSide.SELL and bar.close == band.lower)
    )
    if blocked:
        return (
            ConstraintDecision(
                False,
                RejectionCode.PRICE_LIMIT,
                "one-price limit board blocks this order direction",
            ),
            band,
        )
    return ConstraintDecision(True), band


def fill_price_within_limits(
    price: Decimal, bar: RawExecutionBar, band: PriceLimitBand
) -> bool:
    return bar.low <= price <= bar.high and band.lower <= price <= band.upper
