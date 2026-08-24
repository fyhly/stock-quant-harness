"""Basic deterministic portfolio constraints and intent-only integration."""

from decimal import Decimal, ROUND_DOWN

from stock_quant.portfolio.equal_weight import (
    PortfolioConstructionError,
    PortfolioWeight,
    PortfolioWeights,
)


def apply_basic_constraints(
    portfolio: PortfolioWeights,
    *,
    single_name_cap: Decimal,
    cash_floor: Decimal,
    gross_cap: Decimal,
    quantum: Decimal,
) -> PortfolioWeights:
    parameters = (single_name_cap, cash_floor, gross_cap)
    if (
        any(
            not value.is_finite() or not Decimal(0) <= value <= Decimal(1)
            for value in parameters
        )
        or not quantum.is_finite()
        or quantum <= 0
    ):
        raise PortfolioConstructionError("constraint parameters must be in [0, 1]")
    ids = tuple(row.security_id for row in portfolio.weights)
    gross = sum((row.weight for row in portfolio.weights), Decimal(0))
    if ids != tuple(sorted(set(ids))) or gross + portfolio.cash_weight != Decimal(1):
        raise PortfolioConstructionError(
            "input portfolio must be sorted and normalized"
        )
    capped = tuple(
        (row.security_id, min(row.weight, single_name_cap)) for row in portfolio.weights
    )
    capped_gross = sum((weight for _, weight in capped), Decimal(0))
    allowed = min(gross_cap, Decimal(1) - cash_floor)
    scale = (
        Decimal(1)
        if capped_gross <= allowed or capped_gross == 0
        else allowed / capped_gross
    )
    rounded = tuple(
        (security, (weight * scale).quantize(quantum, rounding=ROUND_DOWN))
        for security, weight in capped
    )
    constrained_gross = sum((weight for _, weight in rounded), Decimal(0))
    residual = (
        allowed - constrained_gross
        if capped_gross > allowed
        else capped_gross - constrained_gross
    )
    return PortfolioWeights(
        tuple(
            PortfolioWeight(security, weight)
            for security, weight in rounded
            if weight > 0
        ),
        Decimal(1) - constrained_gross,
        residual,
    )
