"""Explicit Decimal research metric formulas and conventions."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


class MetricInputError(ValueError):
    pass


@dataclass(frozen=True)
class StandardMetrics:
    total_return: Decimal
    maximum_drawdown: Decimal
    annualized_volatility: Decimal
    one_way_turnover: Decimal
    cost_ratio: Decimal
    periods: int
    annualization_periods: int
    convention: str = "simple-return,population-vol,peak-drawdown,half-gross-turnover"


def standard_metrics(
    equity: Iterable[Decimal],
    traded_notionals: Iterable[Decimal],
    costs: Iterable[Decimal],
    *,
    annualization_periods: int = 252,
) -> StandardMetrics:
    values, trades, fees = tuple(equity), tuple(traded_notionals), tuple(costs)
    if not values:
        raise MetricInputError("equity series cannot be empty")
    if annualization_periods <= 0 or any(
        not value.is_finite() or value <= 0 for value in values
    ):
        raise MetricInputError("equity and annualization must be positive finite")
    if any(not value.is_finite() or value < 0 for value in trades + fees):
        raise MetricInputError("trades and costs must be nonnegative finite")
    returns = tuple(
        current / prior - Decimal(1) for prior, current in zip(values, values[1:])
    )
    if returns:
        mean = sum(returns, Decimal(0)) / Decimal(len(returns))
        variance = sum(
            ((value - mean) ** 2 for value in returns), Decimal(0)
        ) / Decimal(len(returns))
        volatility = variance.sqrt() * Decimal(annualization_periods).sqrt()
    else:
        volatility = Decimal(0)
    peak, drawdown = values[0], Decimal(0)
    for value in values:
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - Decimal(1))
    average = sum(values, Decimal(0)) / Decimal(len(values))
    return StandardMetrics(
        values[-1] / values[0] - Decimal(1),
        drawdown,
        volatility,
        sum(trades, Decimal(0)) / (Decimal(2) * average),
        sum(fees, Decimal(0)) / values[0],
        len(returns),
        annualization_periods,
    )
