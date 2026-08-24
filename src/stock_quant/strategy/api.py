"""Execution-independent point-in-time strategy contracts."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import re
from typing import Iterable, Optional, Tuple

from stock_quant.domain import SecurityId, TradingDay


_IDENTITY = re.compile(r"^[0-9a-f]{64}$")


class StrategyContractError(ValueError):
    pass


@dataclass(frozen=True)
class FeatureScore:
    security_id: SecurityId
    value: Optional[Decimal]
    available_time: datetime
    feature_identity: str


@dataclass(frozen=True)
class StrategySnapshot:
    decision_day: TradingDay
    decision_cutoff: datetime
    scores: Tuple[FeatureScore, ...]
    universe_identity: str
    config_identity: str
    data_identity: str


@dataclass(frozen=True)
class ScoreIntent:
    decision_day: TradingDay
    scores: Tuple[FeatureScore, ...]
    lineage: Tuple[str, str, str]


def create_score_intent(
    decision_day: TradingDay,
    decision_cutoff: datetime,
    scores: Iterable[FeatureScore],
    *,
    universe_identity: str,
    config_identity: str,
    data_identity: str,
) -> ScoreIntent:
    if decision_cutoff.tzinfo is None:
        raise StrategyContractError("decision cutoff must be timezone-aware")
    rows = tuple(sorted(scores, key=lambda row: row.security_id))
    ids = tuple(row.security_id for row in rows)
    if not rows or len(set(ids)) != len(ids):
        raise StrategyContractError("scores must be non-empty and unique")
    if any(row.available_time > decision_cutoff for row in rows):
        raise StrategyContractError("feature unavailable at decision cutoff")
    if any(
        row.available_time.tzinfo is None
        or (row.value is not None and not row.value.is_finite())
        or not _IDENTITY.fullmatch(row.feature_identity)
        for row in rows
    ):
        raise StrategyContractError("invalid feature score or identity")
    lineage = (universe_identity, config_identity, data_identity)
    if any(not _IDENTITY.fullmatch(value) for value in lineage):
        raise StrategyContractError("invalid strategy lineage identity")
    return ScoreIntent(decision_day, rows, lineage)
