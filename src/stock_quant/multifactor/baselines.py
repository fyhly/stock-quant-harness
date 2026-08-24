"""Deterministic top-N equal and shifted-score baseline candidates."""

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
from typing import Iterable, Tuple

from stock_quant.multifactor.neutralize import NeutralizedScore
from stock_quant.portfolio import PortfolioWeights, equal_weight
from stock_quant.portfolio.score_weight import (
    NegativeScorePolicy,
    PortfolioScore,
    ScoreMissingPolicy,
    ZeroScorePolicy,
    score_weight,
)


class BaselineAllocationError(ValueError):
    pass


@dataclass(frozen=True)
class BaselineCandidate:
    name: str
    portfolio: PortfolioWeights
    config_identity: str
    selected_ids: Tuple[str, ...]
    method: str


def baseline_allocators(
    scores: Iterable[NeutralizedScore],
    *,
    top_n: int,
    cash_target: Decimal,
    quantum: Decimal,
) -> Tuple[BaselineCandidate, ...]:
    rows = tuple(scores)
    if top_n <= 0 or top_n > len(rows) or not rows:
        raise BaselineAllocationError("top_n must fit a nonempty cross-section")
    dates = {row.as_of for row in rows}
    ids = tuple(row.security_id for row in rows)
    if len(dates) != 1 or len(set(ids)) != len(ids):
        raise BaselineAllocationError(
            "baseline inputs must be one unique date cross-section"
        )
    selected = tuple(
        sorted(rows, key=lambda row: (-row.residual_score, row.security_id))[:top_n]
    )
    selected_ids = tuple(str(row.security_id) for row in selected)
    equal = equal_weight(
        (row.security_id for row in selected), cash_target=cash_target, quantum=quantum
    )
    minimum = min(row.residual_score for row in selected)
    shifted = tuple(
        PortfolioScore(row.security_id, row.residual_score - minimum + quantum)
        for row in selected
    )
    proportional = score_weight(
        shifted,
        cash_target=cash_target,
        quantum=quantum,
        negative_policy=NegativeScorePolicy.REJECT,
        zero_policy=ZeroScorePolicy.EQUAL_WEIGHT,
        missing_policy=ScoreMissingPolicy.REJECT,
    )
    base = {
        "top_n": top_n,
        "cash_target": str(cash_target),
        "quantum": str(quantum),
        "selected_ids": selected_ids,
    }

    def identity(method: str) -> str:
        return hashlib.sha256(
            json.dumps(
                {**base, "method": method}, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()

    return (
        BaselineCandidate(
            "TOP_N_EQUAL", equal, identity("TOP_N_EQUAL"), selected_ids, "TOP_N_EQUAL"
        ),
        BaselineCandidate(
            "TOP_N_SHIFTED_SCORE",
            proportional,
            identity("TOP_N_SHIFTED_SCORE"),
            selected_ids,
            "SHIFT_MIN_PLUS_QUANTUM_THEN_PROPORTIONAL",
        ),
    )
