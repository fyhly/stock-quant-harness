"""Strictly date-aligned cross-sectional factor diagnostics."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Mapping, Tuple


class FactorAnalyticsError(ValueError):
    pass


@dataclass(frozen=True)
class FactorPoint:
    security_id: str
    feature_date: date
    feature_available_at: datetime
    label_date: date
    score: Decimal
    forward_return: Decimal


@dataclass(frozen=True)
class QuantileSummary:
    quantile: int
    count: int
    mean_forward_return: Decimal


@dataclass(frozen=True)
class DailyFactorAnalytics:
    feature_date: date
    sample_count: int
    ic: Decimal
    rank_ic: Decimal
    quantiles: Tuple[QuantileSummary, ...]
    missing_rule: str = "REJECT"
    tie_rule: str = "AVERAGE_RANK"


def _correlation(left: Tuple[Decimal, ...], right: Tuple[Decimal, ...]) -> Decimal:
    left_mean = sum(left, Decimal(0)) / Decimal(len(left))
    right_mean = sum(right, Decimal(0)) / Decimal(len(right))
    covariance = sum(
        ((x - left_mean) * (y - right_mean) for x, y in zip(left, right)),
        Decimal(0),
    )
    left_ss = sum(((x - left_mean) ** 2 for x in left), Decimal(0))
    right_ss = sum(((y - right_mean) ** 2 for y in right), Decimal(0))
    if left_ss == 0 or right_ss == 0:
        raise FactorAnalyticsError(
            "correlation is undefined for a constant cross-section"
        )
    return covariance / (left_ss * right_ss).sqrt()


def _average_ranks(values: Tuple[Decimal, ...]) -> Tuple[Decimal, ...]:
    ranks = [Decimal(0)] * len(values)
    ordered = sorted(enumerate(values), key=lambda item: (item[1], item[0]))
    cursor = 0
    while cursor < len(ordered):
        end = cursor + 1
        while end < len(ordered) and ordered[end][1] == ordered[cursor][1]:
            end += 1
        rank = (Decimal(cursor + 1) + Decimal(end)) / Decimal(2)
        for index, _ in ordered[cursor:end]:
            ranks[index] = rank
        cursor = end
    return tuple(ranks)


def factor_analytics(
    points: Iterable[FactorPoint],
    decision_cutoffs: Mapping[date, datetime],
    *,
    quantile_count: int = 5,
) -> Tuple[DailyFactorAnalytics, ...]:
    """Compute diagnostics independently per date; reject missing/PIT-invalid rows."""
    if quantile_count <= 0:
        raise FactorAnalyticsError("quantile_count must be positive")
    grouped: dict[date, list[FactorPoint]] = {}
    seen: set[tuple[date, str]] = set()
    for point in points:
        if (
            not point.security_id
            or not point.score.is_finite()
            or not point.forward_return.is_finite()
        ):
            raise FactorAnalyticsError(
                "factor rows cannot contain missing/non-finite values"
            )
        cutoff = decision_cutoffs.get(point.feature_date)
        if cutoff is None or point.feature_available_at > cutoff:
            raise FactorAnalyticsError(
                "feature was not available at the decision cutoff"
            )
        if point.label_date <= point.feature_date:
            raise FactorAnalyticsError(
                "forward label must occur after the feature date"
            )
        key = (point.feature_date, point.security_id)
        if key in seen:
            raise FactorAnalyticsError("duplicate security in a date cross-section")
        seen.add(key)
        grouped.setdefault(point.feature_date, []).append(point)
    results = []
    for feature_date in sorted(grouped):
        rows = sorted(
            grouped[feature_date], key=lambda row: (row.score, row.security_id)
        )
        if len(rows) < 2:
            raise FactorAnalyticsError("each date needs at least two observations")
        scores = tuple(row.score for row in rows)
        returns = tuple(row.forward_return for row in rows)
        buckets: list[list[Decimal]] = [[] for _ in range(quantile_count)]
        for index, row in enumerate(rows):
            bucket = min(index * quantile_count // len(rows), quantile_count - 1)
            buckets[bucket].append(row.forward_return)
        summaries = tuple(
            QuantileSummary(
                index + 1,
                len(bucket),
                sum(bucket, Decimal(0)) / Decimal(len(bucket))
                if bucket
                else Decimal(0),
            )
            for index, bucket in enumerate(buckets)
        )
        results.append(
            DailyFactorAnalytics(
                feature_date,
                len(rows),
                _correlation(scores, returns),
                _correlation(_average_ranks(scores), _average_ranks(returns)),
                summaries,
            )
        )
    return tuple(results)
