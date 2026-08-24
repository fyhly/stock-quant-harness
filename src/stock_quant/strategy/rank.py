"""Stable explainable rank and top-N selection."""

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Tuple

from stock_quant.domain import SecurityId
from stock_quant.strategy.api import FeatureScore, StrategyContractError


class RankMissingPolicy(str, Enum):
    EXCLUDE = "EXCLUDE"
    REJECT = "REJECT"


class BoundaryTiePolicy(str, Enum):
    INCLUDE = "INCLUDE"
    SECURITY_ID = "SECURITY_ID"


@dataclass(frozen=True)
class SelectionRecord:
    security_id: SecurityId
    rank: int
    selected: bool
    reason: str


@dataclass(frozen=True)
class RankedSelection:
    selected: Tuple[SecurityId, ...]
    records: Tuple[SelectionRecord, ...]


def select_top_n(
    scores: Iterable[FeatureScore],
    *,
    top_n: int,
    ascending: bool,
    missing_policy: RankMissingPolicy,
    boundary_ties: BoundaryTiePolicy,
) -> RankedSelection:
    rows = tuple(scores)
    if top_n <= 0:
        raise StrategyContractError("top_n must be positive")
    ids = tuple(row.security_id for row in rows)
    if not rows or len(ids) != len(set(ids)):
        raise StrategyContractError("scores must be non-empty and unique")
    missing = tuple(row for row in rows if row.value is None)
    if missing and missing_policy is RankMissingPolicy.REJECT:
        raise StrategyContractError("missing score rejected by policy")
    observed = tuple(row for row in rows if row.value is not None)
    ordered = tuple(
        sorted(
            observed,
            key=lambda row: (
                row.value if ascending else -row.value,  # type: ignore[operator]
                row.security_id,
            ),
        )
    )
    chosen = list(ordered[:top_n])
    if chosen and boundary_ties is BoundaryTiePolicy.INCLUDE:
        boundary = chosen[-1].value
        chosen.extend(row for row in ordered[top_n:] if row.value == boundary)
    selected = tuple(sorted(row.security_id for row in chosen))
    rank_by_id = {}
    previous_value = None
    current_rank = 0
    for index, row in enumerate(ordered):
        if index == 0 or row.value != previous_value:
            current_rank = index + 1
            previous_value = row.value
        rank_by_id[row.security_id] = current_rank
    records = []
    for row in sorted(rows, key=lambda item: item.security_id):
        if row.value is None:
            records.append(SelectionRecord(row.security_id, 0, False, "MISSING_SCORE"))
        elif row.security_id in selected:
            records.append(
                SelectionRecord(
                    row.security_id, rank_by_id[row.security_id], True, "TOP_N"
                )
            )
        else:
            records.append(
                SelectionRecord(
                    row.security_id, rank_by_id[row.security_id], False, "BELOW_CUTOFF"
                )
            )
    return RankedSelection(selected, tuple(records))
