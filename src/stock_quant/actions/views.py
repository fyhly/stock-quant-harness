"""Strongly typed research-only adjusted price views."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Tuple

from stock_quant.actions.factors import AdjustmentFactorSeries
from stock_quant.data import DailyBarSeries
from stock_quant.domain import SecurityId, TradingDay


class ResearchPriceExecutionError(TypeError):
    """Raised when an adjusted research price is requested for execution."""


@dataclass(frozen=True)
class ForwardAdjustedBar:
    """Forward-adjusted OHLC; never a tradable market observation."""

    security_id: SecurityId
    trading_day: TradingDay
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    factor: Decimal
    raw_volume: int
    raw_amount: Decimal
    factor_series_id: str
    event_lineage: Tuple[str, ...]

    @property
    def research_only(self) -> bool:
        return True

    def as_execution_price(self) -> Decimal:
        raise ResearchPriceExecutionError(
            "forward-adjusted research prices cannot be execution prices"
        )


@dataclass(frozen=True)
class ForwardAdjustedSeries:
    security_id: SecurityId
    knowledge_cutoff: date
    factor_series_id: str
    bars: Tuple[ForwardAdjustedBar, ...]
    event_lineage: Tuple[str, ...]


def forward_adjusted_view(
    raw: DailyBarSeries, factors: AdjustmentFactorSeries
) -> ForwardAdjustedSeries:
    """Adjust historical OHLC while leaving the latest side raw-scaled."""

    if not isinstance(raw, DailyBarSeries):
        raise TypeError("raw must be a DailyBarSeries")
    if not isinstance(factors, AdjustmentFactorSeries):
        raise TypeError("factors must be an AdjustmentFactorSeries")
    if raw.security_id != factors.security_id:
        raise ValueError("raw and factor security identities must match")
    if any(bar.trading_day.value > factors.knowledge_cutoff for bar in raw.bars):
        raise ValueError("raw bars cannot extend beyond factor knowledge_cutoff")
    adjusted = []
    for bar in raw.bars:
        factor = factors.forward_factor_for(bar.trading_day.value)
        adjusted.append(
            ForwardAdjustedBar(
                bar.security_id,
                bar.trading_day,
                bar.open * factor,
                bar.high * factor,
                bar.low * factor,
                bar.close * factor,
                factor,
                bar.volume,
                bar.amount,
                factors.series_id,
                factors.event_lineage,
            )
        )
    return ForwardAdjustedSeries(
        raw.security_id,
        factors.knowledge_cutoff,
        factors.series_id,
        tuple(adjusted),
        factors.event_lineage,
    )
