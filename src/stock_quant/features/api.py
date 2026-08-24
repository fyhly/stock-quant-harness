"""Deterministic point-in-time feature contracts."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Iterable, Tuple

from stock_quant.domain import SecurityId, TradingDay


class FeatureContractError(ValueError):
    pass


class FeatureScope(str, Enum):
    TIME_SERIES = "TIME_SERIES"
    CROSS_SECTION = "CROSS_SECTION"


@dataclass(frozen=True)
class FeatureRequest:
    name: str
    scope: FeatureScope
    securities: Tuple[SecurityId, ...]
    decision_day: TradingDay
    decision_cutoff: datetime

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise FeatureContractError("feature name cannot be empty")
        if self.decision_cutoff.tzinfo is None:
            raise FeatureContractError("decision_cutoff must be timezone-aware")
        if not self.securities or self.securities != tuple(
            sorted(set(self.securities))
        ):
            raise FeatureContractError("securities must be sorted and unique")


@dataclass(frozen=True)
class FeatureObservation:
    security_id: SecurityId
    event_time: datetime
    available_time: datetime
    value: Decimal
    source_identity: str

    def __post_init__(self) -> None:
        if self.event_time.tzinfo is None or self.available_time.tzinfo is None:
            raise FeatureContractError("observation times must be timezone-aware")
        if not self.value.is_finite() or not self.source_identity.strip():
            raise FeatureContractError("observation value/source must be valid")


@dataclass(frozen=True)
class FeatureResult:
    request: FeatureRequest
    observations: Tuple[FeatureObservation, ...]
    formula_version: str
    lineage: Tuple[str, ...]


def build_feature_result(
    request: FeatureRequest,
    observations: Iterable[FeatureObservation],
    *,
    formula_version: str,
    lineage: Iterable[str],
) -> FeatureResult:
    rows = tuple(observations)
    if not formula_version.strip():
        raise FeatureContractError("formula_version cannot be empty")
    if any(row.available_time > request.decision_cutoff for row in rows):
        raise FeatureContractError("observation unavailable at decision cutoff")
    keys = tuple((row.security_id, row.event_time) for row in rows)
    if len(set(keys)) != len(keys):
        raise FeatureContractError("duplicate observation fact")
    if keys != tuple(sorted(keys)):
        raise FeatureContractError("observations must be deterministically ordered")
    present = {row.security_id for row in rows}
    if present != set(request.securities):
        raise FeatureContractError("missing or unexpected security observations")
    frozen_lineage = tuple(lineage)
    if not frozen_lineage or len(set(frozen_lineage)) != len(frozen_lineage):
        raise FeatureContractError("lineage must be non-empty and unique")
    return FeatureResult(request, rows, formula_version, frozen_lineage)
