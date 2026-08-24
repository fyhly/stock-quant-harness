"""Typed unadjusted price view; the only action-layer execution-price API."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Tuple

from stock_quant.data import DailyBarSeries
from stock_quant.domain import SecurityId, TradingDay


class ExecutionPriceField(str, Enum):
    OPEN = "OPEN"
    HIGH = "HIGH"
    LOW = "LOW"
    CLOSE = "CLOSE"


@dataclass(frozen=True)
class RawExecutionBar:
    security_id: SecurityId
    trading_day: TradingDay
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    amount: Decimal
    source_schema_version: str


@dataclass(frozen=True)
class RawExecutionPriceView:
    """Unadjusted normalized market observations, never research adjustments."""

    security_id: SecurityId
    bars: Tuple[RawExecutionBar, ...]


def raw_execution_price_view(raw: DailyBarSeries) -> RawExecutionPriceView:
    if not isinstance(raw, DailyBarSeries):
        raise TypeError("execution view requires a normalized DailyBarSeries")
    return RawExecutionPriceView(
        raw.security_id,
        tuple(
            RawExecutionBar(
                bar.security_id,
                bar.trading_day,
                bar.open,
                bar.high,
                bar.low,
                bar.close,
                bar.volume,
                bar.amount,
                bar.schema_version,
            )
            for bar in raw.bars
        ),
    )


def execution_price(
    view: RawExecutionPriceView,
    trading_day: TradingDay,
    field: ExecutionPriceField,
) -> Decimal:
    if not isinstance(view, RawExecutionPriceView):
        raise TypeError("execution_price accepts only RawExecutionPriceView")
    if not isinstance(trading_day, TradingDay):
        raise TypeError("trading_day must be a TradingDay")
    if not isinstance(field, ExecutionPriceField):
        raise TypeError("field must be an ExecutionPriceField")
    for bar in view.bars:
        if bar.trading_day == trading_day:
            value = getattr(bar, field.value.lower())
            assert isinstance(value, Decimal)
            return value
    raise KeyError(f"no raw execution bar for {trading_day.value.isoformat()}")
