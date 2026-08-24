"""PIT factor-ranked quantile forward-return comparisons."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Mapping, Tuple

from stock_quant.research.factor_analytics import FactorAnalyticsError, FactorPoint


@dataclass(frozen=True)
class QuantilePortfolio:
    feature_date: date
    label_date: date
    quantile: int
    securities: Tuple[str, ...]
    gross_return: Decimal
    net_return: Decimal
    cost_rate: Decimal
    tie_rule: str = "AVERAGE_RANK_KEEP_TIES"
    cost_convention: str = "ROUND_TRIP_RATE_SUBTRACTED_FROM_FORWARD_RETURN"


def quantile_backtests(
    points: Iterable[FactorPoint],
    decision_cutoffs: Mapping[date, datetime],
    *,
    quantile_count: int,
    round_trip_cost_rate: Decimal,
) -> Tuple[QuantilePortfolio, ...]:
    if (
        quantile_count <= 0
        or round_trip_cost_rate < 0
        or not round_trip_cost_rate.is_finite()
    ):
        raise FactorAnalyticsError("invalid quantile or cost convention")
    grouped: dict[date, list[FactorPoint]] = {}
    seen: set[tuple[date, str]] = set()
    for point in points:
        cutoff = decision_cutoffs.get(point.feature_date)
        if cutoff is None or point.feature_available_at > cutoff:
            raise FactorAnalyticsError(
                "feature was not available at the decision cutoff"
            )
        if point.label_date <= point.feature_date:
            raise FactorAnalyticsError("forward label must occur after ranking")
        if not point.score.is_finite() or not point.forward_return.is_finite():
            raise FactorAnalyticsError("missing/non-finite factor input")
        key = (point.feature_date, point.security_id)
        if key in seen:
            raise FactorAnalyticsError("duplicate security in date cross-section")
        seen.add(key)
        grouped.setdefault(point.feature_date, []).append(point)
    output = []
    for feature_date in sorted(grouped):
        rows = sorted(
            grouped[feature_date], key=lambda item: (item.score, item.security_id)
        )
        label_dates = {row.label_date for row in rows}
        if len(label_dates) != 1:
            raise FactorAnalyticsError(
                "forward labels must share one date per cross-section"
            )
        buckets: list[list[FactorPoint]] = [[] for _ in range(quantile_count)]
        start = 0
        while start < len(rows):
            end = start + 1
            while end < len(rows) and rows[end].score == rows[start].score:
                end += 1
            average_rank_zero_based = Decimal(start + end - 1) / Decimal(2)
            bucket = min(
                int(average_rank_zero_based * quantile_count / len(rows)),
                quantile_count - 1,
            )
            buckets[bucket].extend(rows[start:end])
            start = end
        label_date = next(iter(label_dates))
        for index, bucket_rows in enumerate(buckets):
            gross = (
                sum((row.forward_return for row in bucket_rows), Decimal(0))
                / Decimal(len(bucket_rows))
                if bucket_rows
                else Decimal(0)
            )
            output.append(
                QuantilePortfolio(
                    feature_date,
                    label_date,
                    index + 1,
                    tuple(sorted(row.security_id for row in bucket_rows)),
                    gross,
                    gross - round_trip_cost_rate if bucket_rows else Decimal(0),
                    round_trip_cost_rate,
                )
            )
    return tuple(output)
