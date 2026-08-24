"""Point-in-time deterministic sector exposure limits."""

from decimal import Decimal, ROUND_DOWN
from typing import Dict, Iterable, Tuple

from stock_quant.domain import TradingDay
from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.risk.api import PITClassification, RiskAdjustment, RiskContractError


def apply_sector_limit(
    portfolio: PortfolioWeights,
    classifications: Iterable[PITClassification],
    *,
    as_of: TradingDay,
    cap: Decimal,
    quantum: Decimal,
) -> Tuple[PortfolioWeights, Tuple[RiskAdjustment, ...]]:
    if (
        not cap.is_finite()
        or not Decimal(0) <= cap <= Decimal(1)
        or not quantum.is_finite()
        or quantum <= 0
    ):
        raise RiskContractError("invalid sector cap or quantum")
    rows = tuple(classifications)
    mapping = {row.security_id: row for row in rows}
    ids = {row.security_id for row in portfolio.weights}
    if len(mapping) != len(rows) or set(mapping) != ids:
        raise RiskContractError("missing or duplicate sector history")
    if any(row.as_of != as_of for row in rows):
        raise RiskContractError("sector history as-of mismatch")
    totals: Dict[str, Decimal] = {}
    for weight in portfolio.weights:
        code = mapping[weight.security_id].industry_code
        totals[code] = totals.get(code, Decimal(0)) + weight.weight
    output, adjustments = [], []
    for weight in sorted(portfolio.weights):
        total = totals[mapping[weight.security_id].industry_code]
        scale = Decimal(1) if total <= cap or total == 0 else cap / total
        after = (weight.weight * scale).quantize(quantum, rounding=ROUND_DOWN)
        output.append(PortfolioWeight(weight.security_id, after))
        if after != weight.weight:
            adjustments.append(
                RiskAdjustment(
                    "SECTOR",
                    weight.security_id,
                    str(weight.weight),
                    str(after),
                    f"SECTOR_CAP:{mapping[weight.security_id].industry_code}",
                )
            )
    gross = sum((row.weight for row in output), Decimal(0))
    return PortfolioWeights(tuple(output), Decimal(1) - gross, Decimal(0)), tuple(
        adjustments
    )
