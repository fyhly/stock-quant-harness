"""Exact deterministic single-name clipping."""

from decimal import Decimal
from typing import Tuple

from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.risk.api import RiskAdjustment, RiskContractError


def apply_single_name_limit(
    portfolio: PortfolioWeights, cap: Decimal
) -> Tuple[PortfolioWeights, Tuple[RiskAdjustment, ...]]:
    if not cap.is_finite() or not Decimal(0) <= cap <= Decimal(1):
        raise RiskContractError("single-name cap must be in [0, 1]")
    weights, adjustments = [], []
    for row in sorted(portfolio.weights):
        after = min(row.weight, cap)
        weights.append(PortfolioWeight(row.security_id, after))
        if after != row.weight:
            adjustments.append(
                RiskAdjustment(
                    "SINGLE_NAME",
                    row.security_id,
                    str(row.weight),
                    str(after),
                    "SINGLE_NAME_CAP",
                )
            )
    gross = sum((row.weight for row in weights), Decimal(0))
    return PortfolioWeights(tuple(weights), Decimal(1) - gross, Decimal(0)), tuple(
        adjustments
    )
