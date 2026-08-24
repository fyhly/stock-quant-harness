"""Versioned adjustment factors derived from known, effective actions."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import hashlib
import json
from typing import Dict, Iterable, Mapping, Tuple

from stock_quant.actions.model import (
    BonusShareEvent,
    CashDividend,
    CorporateActionType,
    RightsIssue,
)
from stock_quant.domain import SecurityId


@dataclass(frozen=True)
class AdjustmentFactorPoint:
    ex_date: date
    ratio: Decimal
    reference_price: Decimal
    theoretical_ex_price: Decimal
    event_ids: Tuple[str, ...]


@dataclass(frozen=True)
class AdjustmentFactorSeries:
    security_id: SecurityId
    knowledge_cutoff: date
    version: str
    points: Tuple[AdjustmentFactorPoint, ...]
    series_id: str

    @property
    def event_lineage(self) -> Tuple[str, ...]:
        return tuple(event_id for point in self.points for event_id in point.event_ids)

    def forward_factor_for(self, bar_date: date) -> Decimal:
        """Multiply ratios for known ex dates strictly after the raw bar date."""

        return _product(
            point.ratio
            for point in self.points
            if bar_date < point.ex_date <= self.knowledge_cutoff
        )

    def backward_factor_for(self, bar_date: date) -> Decimal:
        """Divide post-ex raw prices by ratios already effective by bar date."""

        return _product(
            Decimal(1) / point.ratio
            for point in self.points
            if point.ex_date <= bar_date <= self.knowledge_cutoff
        )


def build_adjustment_factors(
    security_id: SecurityId,
    actions: Iterable[CorporateActionType],
    *,
    reference_prices: Mapping[date, Decimal],
    knowledge_cutoff: date,
    version: str,
) -> AdjustmentFactorSeries:
    """Build same-day atomic factors using unadjusted pre-ex references."""

    if not isinstance(security_id, SecurityId):
        raise TypeError("security_id must be a SecurityId")
    if type(knowledge_cutoff) is not date:
        raise TypeError("knowledge_cutoff must be a date, not a datetime")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("factor version must be non-empty")
    supplied = tuple(actions)
    supported = (CashDividend, BonusShareEvent, RightsIssue)
    if any(not isinstance(action, supported) for action in supplied):
        raise TypeError("unsupported corporate action type")
    if any(action.security_id != security_id for action in supplied):
        raise ValueError("all actions must belong to the requested security")
    ids = tuple(action.event_id for action in supplied)
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate corporate action event_id")
    known = tuple(
        action
        for action in supplied
        if action.announcement_date <= knowledge_cutoff
        and action.ex_date <= knowledge_cutoff
    )
    grouped: Dict[date, list[CorporateActionType]] = {}
    for action in known:
        grouped.setdefault(action.ex_date, []).append(action)

    points = []
    for ex_date in sorted(grouped):
        reference = reference_prices.get(ex_date)
        if (
            not isinstance(reference, Decimal)
            or not reference.is_finite()
            or reference <= 0
        ):
            raise ValueError("a positive finite Decimal reference is required per ex date")
        cash = Decimal(0)
        bonus = Decimal(0)
        rights = Decimal(0)
        rights_value = Decimal(0)
        events = sorted(grouped[ex_date], key=lambda action: action.event_id)
        for action in events:
            if isinstance(action, CashDividend):
                cash += action.cash_per_share
            elif isinstance(action, BonusShareEvent):
                bonus += action.total_ratio
            else:
                rights += action.rights_ratio
                rights_value += action.rights_ratio * action.subscription_price
        theoretical = (reference - cash + rights_value) / (
            Decimal(1) + bonus + rights
        )
        if theoretical <= 0 or not theoretical.is_finite():
            raise ValueError("corporate actions imply nonpositive theoretical ex price")
        points.append(
            AdjustmentFactorPoint(
                ex_date,
                theoretical / reference,
                reference,
                theoretical,
                tuple(action.event_id for action in events),
            )
        )
    payload = {
        "knowledge_cutoff": knowledge_cutoff.isoformat(),
        "points": [
            {
                "event_ids": list(point.event_ids),
                "ex_date": point.ex_date.isoformat(),
                "ratio": str(point.ratio),
                "reference_price": str(point.reference_price),
                "theoretical_ex_price": str(point.theoretical_ex_price),
            }
            for point in points
        ],
        "security_id": str(security_id),
        "version": version,
    }
    series_id = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return AdjustmentFactorSeries(
        security_id, knowledge_cutoff, version, tuple(points), series_id
    )


def _product(values: Iterable[Decimal]) -> Decimal:
    result = Decimal(1)
    for value in values:
        result *= value
    return result
