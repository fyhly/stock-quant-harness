"""One-way turnover cap via deterministic proportional transition."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Tuple

from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.domain import SecurityId
from stock_quant.risk.api import RiskAdjustment, RiskContractError


@dataclass(frozen=True)
class TurnoverResult:
    portfolio: PortfolioWeights
    requested_turnover: Decimal
    achieved_turnover: Decimal
    adjustments: Tuple[RiskAdjustment, ...]


def apply_turnover_limit(
    proposed: PortfolioWeights,
    current: PortfolioWeights,
    cap: Decimal,
) -> TurnoverResult:
    if not cap.is_finite() or not Decimal(0) <= cap <= Decimal(1):
        raise RiskContractError("turnover cap must be in [0, 1]")
    proposed_map = {row.security_id: row.weight for row in proposed.weights}
    current_map = {row.security_id: row.weight for row in current.weights}
    securities = tuple(sorted(set(proposed_map) | set(current_map)))
    requested = _turnover(
        proposed_map, proposed.cash_weight, current_map, current.cash_weight
    )
    scale = Decimal(1) if requested <= cap or requested == 0 else cap / requested
    output, adjustments = [], []
    for security in securities:
        before = current_map.get(security, Decimal(0))
        target = proposed_map.get(security, Decimal(0))
        after = before + (target - before) * scale
        if after > 0:
            output.append(PortfolioWeight(security, after))
        if after != target:
            adjustments.append(
                RiskAdjustment(
                    "TURNOVER", security, str(target), str(after), "TURNOVER_CAP"
                )
            )
    cash = current.cash_weight + (proposed.cash_weight - current.cash_weight) * scale
    portfolio = PortfolioWeights(tuple(output), cash, Decimal(0))
    achieved = _turnover(
        {row.security_id: row.weight for row in portfolio.weights},
        cash,
        current_map,
        current.cash_weight,
    )
    return TurnoverResult(portfolio, requested, achieved, tuple(adjustments))


def _turnover(
    proposed: Mapping[SecurityId, Decimal],
    proposed_cash: Decimal,
    current: Mapping[SecurityId, Decimal],
    current_cash: Decimal,
) -> Decimal:
    keys = set(proposed) | set(current)
    distance = sum(
        (
            abs(proposed.get(key, Decimal(0)) - current.get(key, Decimal(0)))
            for key in keys
        ),
        Decimal(0),
    )
    return (distance + abs(proposed_cash - current_cash)) / Decimal(2)
