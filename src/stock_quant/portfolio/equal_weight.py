"""Exact deterministic equal-weight portfolio construction."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Iterable, Tuple

from stock_quant.domain import SecurityId


class PortfolioConstructionError(ValueError):
    pass


@dataclass(frozen=True, order=True)
class PortfolioWeight:
    security_id: SecurityId
    weight: Decimal


@dataclass(frozen=True)
class PortfolioWeights:
    weights: Tuple[PortfolioWeight, ...]
    cash_weight: Decimal
    rounding_residual: Decimal


def equal_weight(
    selected: Iterable[SecurityId],
    *,
    cash_target: Decimal,
    quantum: Decimal,
) -> PortfolioWeights:
    securities = tuple(sorted(selected))
    if len(set(securities)) != len(securities):
        raise PortfolioConstructionError("selection must be unique")
    if (
        not cash_target.is_finite()
        or not Decimal(0) <= cash_target <= Decimal(1)
        or not quantum.is_finite()
        or quantum <= 0
    ):
        raise PortfolioConstructionError("invalid cash target or quantum")
    investable = Decimal(1) - cash_target
    if not securities:
        if investable != 0:
            return PortfolioWeights((), Decimal(1), investable)
        return PortfolioWeights((), cash_target, Decimal(0))
    base = (investable / Decimal(len(securities))).quantize(
        quantum, rounding=ROUND_DOWN
    )
    residual = investable - base * Decimal(len(securities))
    weights = tuple(
        PortfolioWeight(security, base + (residual if index == 0 else Decimal(0)))
        for index, security in enumerate(securities)
    )
    return PortfolioWeights(weights, cash_target, residual)
