"""Configured fail-closed gate before every downstream daily stage."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Iterable, Tuple, TypeVar


T = TypeVar("T")


class DailyQualityFailure(RuntimeError):
    def __init__(self, reasons: Tuple[str, ...]) -> None:
        self.reasons = reasons
        super().__init__("fatal daily quality failure: " + ";".join(reasons))


@dataclass(frozen=True)
class DailyQualityConfig:
    maximum_age_days: int
    minimum_coverage: Decimal
    low_coverage_warning: Decimal


@dataclass(frozen=True)
class DailyQualitySample:
    dataset: str
    age_days: int
    coverage: Decimal
    hash_valid: bool
    schema_valid: bool
    duplicate_count: int
    ohlc_valid: bool
    calendar_valid: bool


@dataclass(frozen=True)
class DailyQualityEvidence:
    passed: bool
    fatal_reasons: Tuple[str, ...]
    warnings: Tuple[str, ...]
    checked_datasets: Tuple[str, ...]


def evaluate_daily_quality(
    samples: Iterable[DailyQualitySample], config: DailyQualityConfig
) -> DailyQualityEvidence:
    rows = tuple(sorted(samples, key=lambda item: item.dataset))
    if config.maximum_age_days < 0 or not Decimal(0) <= config.minimum_coverage <= 1:
        raise ValueError("invalid daily quality config")
    if not rows or len({item.dataset for item in rows}) != len(rows):
        return DailyQualityEvidence(False, ("MISSING_OR_DUPLICATE_DATASET",), (), ())
    fatal, warnings = [], []
    for row in rows:
        prefix = row.dataset + ":"
        if row.age_days < 0 or row.age_days > config.maximum_age_days:
            fatal.append(prefix + "STALE")
        if row.coverage < config.minimum_coverage:
            fatal.append(prefix + "COVERAGE")
        elif row.coverage < config.low_coverage_warning:
            warnings.append(prefix + "LOW_COVERAGE")
        if not row.hash_valid:
            fatal.append(prefix + "HASH")
        if not row.schema_valid:
            fatal.append(prefix + "SCHEMA")
        if row.duplicate_count:
            fatal.append(prefix + "DUPLICATES")
        if not row.ohlc_valid:
            fatal.append(prefix + "OHLC")
        if not row.calendar_valid:
            fatal.append(prefix + "CALENDAR")
    return DailyQualityEvidence(
        not fatal, tuple(fatal), tuple(warnings), tuple(item.dataset for item in rows)
    )


def invoke_after_quality(
    evidence: DailyQualityEvidence, callback: Callable[[], T]
) -> T:
    if not evidence.passed:
        raise DailyQualityFailure(evidence.fatal_reasons)
    return callback()
