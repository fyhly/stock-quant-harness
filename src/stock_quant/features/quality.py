"""Announcement- and revision-aware point-in-time quality factors."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Optional

from stock_quant.domain import SecurityId
from stock_quant.features.api import FeatureContractError


@dataclass(frozen=True)
class StatementObservation:
    security_id: SecurityId
    report_period: date
    announcement_time: datetime
    revision_time: datetime
    net_income: Optional[Decimal]
    equity: Optional[Decimal]
    revenue: Optional[Decimal]
    operating_cash_flow: Optional[Decimal]
    source_identity: str


@dataclass(frozen=True)
class QualityFactors:
    roe: Optional[Decimal]
    net_margin: Optional[Decimal]
    cash_flow_quality: Optional[Decimal]
    report_period: date
    revision_time: datetime
    lineage: str


def quality_factors(
    statements: Iterable[StatementObservation],
    *,
    security_id: SecurityId,
    decision_cutoff: datetime,
) -> QualityFactors:
    rows = tuple(statements)
    if any(
        row.announcement_time > decision_cutoff or row.revision_time > decision_cutoff
        for row in rows
    ):
        raise FeatureContractError("future statement announcement or revision supplied")
    available = tuple(row for row in rows if row.security_id == security_id)
    if not available:
        raise FeatureContractError("missing point-in-time statement")
    period = max(row.report_period for row in available)
    versions = tuple(row for row in available if row.report_period == period)
    selected = max(versions, key=lambda row: row.revision_time)
    return QualityFactors(
        _positive_denominator_ratio(selected.net_income, selected.equity),
        _positive_denominator_ratio(selected.net_income, selected.revenue),
        _positive_denominator_ratio(selected.operating_cash_flow, selected.net_income),
        period,
        selected.revision_time,
        selected.source_identity,
    )


def _positive_denominator_ratio(
    numerator: Optional[Decimal], denominator: Optional[Decimal]
) -> Optional[Decimal]:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    if not numerator.is_finite() or not denominator.is_finite():
        raise FeatureContractError("statement values must be finite")
    return numerator / denominator
