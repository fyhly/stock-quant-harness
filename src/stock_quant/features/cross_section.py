"""Per-date deterministic cross-sectional transforms."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Iterable, Optional, Tuple

from stock_quant.domain import SecurityId, TradingDay
from stock_quant.features.api import FeatureContractError


class MissingPolicy(str, Enum):
    KEEP = "KEEP"
    DROP = "DROP"
    REJECT = "REJECT"


class TiePolicy(str, Enum):
    AVERAGE = "AVERAGE"


class ConstantPolicy(str, Enum):
    ZERO = "ZERO"


@dataclass(frozen=True)
class CrossSectionValue:
    security_id: SecurityId
    fitted_day: TradingDay
    value: Optional[Decimal]


@dataclass(frozen=True)
class TransformedValue:
    security_id: SecurityId
    winsorized: Optional[Decimal]
    standardized: Optional[Decimal]
    rank: Optional[Decimal]


@dataclass(frozen=True)
class CrossSectionResult:
    fitted_day: TradingDay
    values: Tuple[TransformedValue, ...]
    lower_quantile: Decimal
    upper_quantile: Decimal
    missing_policy: MissingPolicy
    tie_policy: TiePolicy
    constant_policy: ConstantPolicy


def cross_sectional_transform(
    values: Iterable[CrossSectionValue],
    *,
    lower_quantile: Decimal,
    upper_quantile: Decimal,
    missing_policy: MissingPolicy,
    tie_policy: TiePolicy = TiePolicy.AVERAGE,
    constant_policy: ConstantPolicy = ConstantPolicy.ZERO,
) -> CrossSectionResult:
    rows = tuple(values)
    if not rows:
        raise FeatureContractError("cross-section cannot be empty")
    days = {row.fitted_day for row in rows}
    if len(days) != 1:
        raise FeatureContractError("cross-section must contain exactly one date")
    ids = tuple(row.security_id for row in rows)
    if len(set(ids)) != len(ids):
        raise FeatureContractError("duplicate cross-sectional security")
    if not Decimal(0) <= lower_quantile < upper_quantile <= Decimal(1):
        raise FeatureContractError("invalid winsorization quantiles")
    if (
        tie_policy is not TiePolicy.AVERAGE
        or constant_policy is not ConstantPolicy.ZERO
    ):
        raise FeatureContractError("unsupported transform policy")
    if missing_policy is MissingPolicy.REJECT and any(
        row.value is None for row in rows
    ):
        raise FeatureContractError("missing cross-sectional value")
    kept = tuple(
        sorted(
            (row for row in rows if row.value is not None),
            key=lambda row: row.security_id,
        )
    )
    if not kept:
        raise FeatureContractError("cross-section has no observed values")
    observed = tuple(row.value for row in kept)
    assert all(value is not None for value in observed)
    numeric = tuple(value for value in observed if value is not None)
    if any(not value.is_finite() for value in numeric):
        raise FeatureContractError("cross-sectional values must be finite")
    low, high = _quantile(numeric, lower_quantile), _quantile(numeric, upper_quantile)
    winsorized = tuple(min(max(value, low), high) for value in numeric)
    mean = sum(winsorized, Decimal(0)) / Decimal(len(winsorized))
    variance = sum(((value - mean) ** 2 for value in winsorized), Decimal(0)) / Decimal(
        len(winsorized)
    )
    standard = variance.sqrt()
    zscores = tuple(
        Decimal(0) if standard == 0 else (value - mean) / standard
        for value in winsorized
    )
    ranks = _average_ranks(winsorized)
    transformed = {
        row.security_id: TransformedValue(row.security_id, win, zscore, rank)
        for row, win, zscore, rank in zip(kept, winsorized, zscores, ranks)
    }
    if missing_policy is MissingPolicy.KEEP:
        transformed.update(
            {
                row.security_id: TransformedValue(row.security_id, None, None, None)
                for row in rows
                if row.value is None
            }
        )
    day = next(iter(days))
    return CrossSectionResult(
        day,
        tuple(transformed[key] for key in sorted(transformed)),
        lower_quantile,
        upper_quantile,
        missing_policy,
        tie_policy,
        constant_policy,
    )


def _quantile(values: Tuple[Decimal, ...], quantile: Decimal) -> Decimal:
    ordered = tuple(sorted(values))
    position = quantile * Decimal(len(ordered) - 1)
    lower = int(position)
    fraction = position - Decimal(lower)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _average_ranks(values: Tuple[Decimal, ...]) -> Tuple[Decimal, ...]:
    ordered = sorted(enumerate(values), key=lambda item: (item[1], item[0]))
    result = [Decimal(0)] * len(values)
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        average = Decimal(index + end - 1) / Decimal(2)
        normalized = (
            Decimal("0.5") if len(values) == 1 else average / Decimal(len(values) - 1)
        )
        for original, _ in ordered[index:end]:
            result[original] = normalized
        index = end
    return tuple(result)
