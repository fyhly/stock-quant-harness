"""Per-date PIT industry demeaning and size residualization."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable, Mapping, Tuple

from stock_quant.domain import SecurityId
from stock_quant.multifactor.combine import CompositeScore
from stock_quant.universe.industry import (
    IndustryMembershipHistory,
    UnknownIndustryHistoryError,
)


class NeutralizationError(ValueError):
    pass


@dataclass(frozen=True)
class NeutralizedScore:
    as_of: date
    security_id: SecurityId
    industry_code: str
    size_exposure: Decimal
    input_score: Decimal
    industry_demeaned: Decimal
    residual_score: Decimal
    method_version: str
    taxonomy_identity: str
    size_identity: str


def neutralize_scores(
    scores: Iterable[CompositeScore],
    history: IndustryMembershipHistory,
    sizes: Mapping[tuple[date, SecurityId], Decimal],
    *,
    size_identity: str,
    method_version: str = "INDUSTRY_DEMEAN_THEN_DAILY_SIZE_OLS_V1",
) -> Tuple[NeutralizedScore, ...]:
    if len(size_identity) != 64 or not method_version:
        raise NeutralizationError("neutralization identities are invalid")
    grouped: dict[date, list[tuple[CompositeScore, str, Decimal]]] = {}
    ordered = tuple(sorted(scores, key=lambda item: (item.as_of, item.security_id)))
    for score in ordered:
        try:
            industry = history.classification_as_of(
                score.security_id, score.as_of
            ).industry_code
            size = sizes[(score.as_of, score.security_id)]
        except UnknownIndustryHistoryError as exc:
            raise NeutralizationError("missing PIT industry classification") from exc
        except KeyError as exc:
            raise NeutralizationError("missing date-aligned size exposure") from exc
        if not score.score.is_finite() or not size.is_finite():
            raise NeutralizationError("score and size must be finite")
        grouped.setdefault(score.as_of, []).append((score, industry, size))
    output = []
    taxonomy = f"{history.taxonomy.name}:{history.taxonomy.version}"
    for as_of in sorted(grouped):
        rows = grouped[as_of]
        industry_totals: dict[str, tuple[Decimal, int]] = {}
        for score, industry, _ in rows:
            total, count = industry_totals.get(industry, (Decimal(0), 0))
            industry_totals[industry] = (total + score.score, count + 1)
        demeaned = tuple(
            score.score
            - industry_totals[industry][0] / Decimal(industry_totals[industry][1])
            for score, industry, _ in rows
        )
        size_values = tuple(size for _, _, size in rows)
        size_mean = sum(size_values, Decimal(0)) / Decimal(len(rows))
        y_mean = sum(demeaned, Decimal(0)) / Decimal(len(rows))
        denominator = sum(
            ((value - size_mean) ** 2 for value in size_values), Decimal(0)
        )
        beta = (
            sum(
                (
                    (size - size_mean) * (value - y_mean)
                    for size, value in zip(size_values, demeaned)
                ),
                Decimal(0),
            )
            / denominator
            if denominator
            else Decimal(0)
        )
        for (score, industry, size), value in zip(rows, demeaned):
            residual = value - y_mean - beta * (size - size_mean)
            output.append(
                NeutralizedScore(
                    as_of,
                    score.security_id,
                    industry,
                    size,
                    score.score,
                    value,
                    residual,
                    method_version,
                    taxonomy,
                    size_identity,
                )
            )
    return tuple(output)
