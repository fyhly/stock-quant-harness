"""PIT sector and explicitly versioned style attribution."""

from dataclasses import dataclass
from decimal import Decimal
import re
from typing import Iterable, Mapping, Tuple

from stock_quant.domain import SecurityId
from stock_quant.universe.industry import (
    IndustryMembershipHistory,
    UnknownIndustryHistoryError,
)
from stock_quant.universe.snapshot import UniverseSnapshot


_SHA = re.compile(r"^[0-9a-f]{64}$")


class ExposureAnalyticsError(ValueError):
    pass


@dataclass(frozen=True)
class ExposurePoint:
    security_id: SecurityId
    weight: Decimal
    security_return: Decimal
    styles: Tuple[Tuple[str, Decimal], ...]


@dataclass(frozen=True)
class ExposureAttribution:
    snapshot_id: str
    taxonomy_identity: str
    style_model_identity: str
    total_return: Decimal
    sector_contributions: Tuple[Tuple[str, Decimal], ...]
    style_exposures: Tuple[Tuple[str, Decimal], ...]
    style_contributions: Tuple[Tuple[str, Decimal], ...]
    residual_return: Decimal


def exposure_attribution(
    snapshot: UniverseSnapshot,
    history: IndustryMembershipHistory,
    points: Iterable[ExposurePoint],
    *,
    style_model_identity: str,
    style_returns: Mapping[str, Decimal],
) -> ExposureAttribution:
    if not _SHA.fullmatch(style_model_identity):
        raise ExposureAnalyticsError("style model identity must be SHA-256")
    rows = tuple(sorted(points, key=lambda item: item.security_id))
    if tuple(row.security_id for row in rows) != snapshot.included:
        raise ExposureAnalyticsError("attribution must exactly cover the PIT universe")
    sector: dict[str, Decimal] = {}
    exposures: dict[str, Decimal] = {}
    for row in rows:
        if (
            not row.weight.is_finite()
            or not row.security_return.is_finite()
            or tuple(name for name, _ in row.styles)
            != tuple(sorted({name for name, _ in row.styles}))
        ):
            raise ExposureAnalyticsError(
                "invalid weight, return, or style classification"
            )
        try:
            industry = history.classification_as_of(
                row.security_id, snapshot.as_of
            ).industry_code
        except UnknownIndustryHistoryError as exc:
            raise ExposureAnalyticsError("missing PIT industry classification") from exc
        sector[industry] = (
            sector.get(industry, Decimal(0)) + row.weight * row.security_return
        )
        for name, value in row.styles:
            if not value.is_finite():
                raise ExposureAnalyticsError("style exposure must be finite")
            exposures[name] = exposures.get(name, Decimal(0)) + row.weight * value
    if set(exposures) != set(style_returns) or any(
        not value.is_finite() for value in style_returns.values()
    ):
        raise ExposureAnalyticsError(
            "style returns must exactly match declared exposures"
        )
    total = sum((row.weight * row.security_return for row in rows), Decimal(0))
    sector_rows = tuple(sorted(sector.items()))
    if sum((value for _, value in sector_rows), Decimal(0)) != total:
        raise ExposureAnalyticsError("sector attribution does not reconcile")
    style_contributions = tuple(
        sorted((name, value * style_returns[name]) for name, value in exposures.items())
    )
    explained = sum((value for _, value in style_contributions), Decimal(0))
    taxonomy = f"{history.taxonomy.name}:{history.taxonomy.version}"
    return ExposureAttribution(
        snapshot.snapshot_id,
        taxonomy,
        style_model_identity,
        total,
        sector_rows,
        tuple(sorted(exposures.items())),
        style_contributions,
        total - explained,
    )
