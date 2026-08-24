"""Final long gross exposure and cash floor enforcement."""

from decimal import Decimal
from typing import Tuple

from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.risk.api import RiskAdjustment, RiskContractError


def apply_cash_exposure_limits(
    portfolio: PortfolioWeights,
    *,
    cash_floor: Decimal,
    gross_cap: Decimal,
) -> Tuple[PortfolioWeights, Tuple[RiskAdjustment, ...]]:
    if any(
        not value.is_finite() or not Decimal(0) <= value <= Decimal(1)
        for value in (cash_floor, gross_cap)
    ):
        raise RiskContractError("cash floor and gross cap must be in [0, 1]")
    if any(row.weight < 0 or not row.weight.is_finite() for row in portfolio.weights):
        raise RiskContractError("negative or nonfinite exposure")
    gross = sum((row.weight for row in portfolio.weights), Decimal(0))
    if gross + portfolio.cash_weight != Decimal(1) or portfolio.cash_weight < 0:
        raise RiskContractError("portfolio is over-allocated or not normalized")
    allowed = min(gross_cap, Decimal(1) - cash_floor)
    scale = Decimal(1) if gross <= allowed or gross == 0 else allowed / gross
    output, adjustments = [], []
    for row in sorted(portfolio.weights):
        after = row.weight * scale
        output.append(PortfolioWeight(row.security_id, after))
        if after != row.weight:
            adjustments.append(
                RiskAdjustment(
                    "EXPOSURE",
                    row.security_id,
                    str(row.weight),
                    str(after),
                    "CASH_GROSS_CAP",
                )
            )
    final_gross = sum((row.weight for row in output), Decimal(0))
    return PortfolioWeights(tuple(output), Decimal(1) - final_gross, Decimal(0)), tuple(
        adjustments
    )
