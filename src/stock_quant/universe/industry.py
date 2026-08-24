"""Effective-dated point-in-time industry classification."""

from dataclasses import dataclass
from datetime import date
import re
from typing import Dict, Iterable, Optional, Tuple

from stock_quant.domain import SecurityId


_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class UnknownIndustryHistoryError(ValueError):
    """Raised when no classification fact covers an as-of date."""


@dataclass(frozen=True, order=True)
class IndustryTaxonomy:
    name: str
    version: str

    def __post_init__(self) -> None:
        if not _SAFE.fullmatch(self.name) or not _SAFE.fullmatch(self.version):
            raise ValueError("invalid industry taxonomy name or version")


@dataclass(frozen=True)
class IndustryMembership:
    """Classification effective on ``[effective_from, effective_to)``."""

    taxonomy: IndustryTaxonomy
    security_id: SecurityId
    industry_code: str
    effective_from: date
    effective_to: Optional[date] = None

    def __post_init__(self) -> None:
        if not isinstance(self.taxonomy, IndustryTaxonomy):
            raise TypeError("taxonomy must be IndustryTaxonomy")
        if not isinstance(self.security_id, SecurityId):
            raise TypeError("security_id must be SecurityId")
        if not isinstance(self.industry_code, str) or not _SAFE.fullmatch(
            self.industry_code
        ):
            raise ValueError("invalid industry_code")
        if type(self.effective_from) is not date:
            raise TypeError("effective_from must be a date")
        if self.effective_to is not None:
            if type(self.effective_to) is not date:
                raise TypeError("effective_to must be a date")
            if self.effective_to <= self.effective_from:
                raise ValueError("effective_to must be after effective_from")

    def contains(self, as_of: date) -> bool:
        return self.effective_from <= as_of and (
            self.effective_to is None or as_of < self.effective_to
        )


class IndustryMembershipHistory:
    """Immutable classification history with gaps preserved as unknown."""

    def __init__(
        self,
        taxonomy: IndustryTaxonomy,
        memberships: Iterable[IndustryMembership],
    ) -> None:
        ordered = tuple(
            sorted(
                memberships,
                key=lambda item: (
                    item.security_id,
                    item.effective_from,
                    item.effective_to or date.max,
                ),
            )
        )
        grouped: Dict[SecurityId, list[IndustryMembership]] = {}
        for membership in ordered:
            if not isinstance(membership, IndustryMembership):
                raise TypeError("memberships must contain IndustryMembership")
            if membership.taxonomy != taxonomy:
                raise ValueError("industry taxonomy identity mismatch")
            grouped.setdefault(membership.security_id, []).append(membership)
        for intervals in grouped.values():
            for previous, current in zip(intervals, intervals[1:]):
                if previous.effective_to is None:
                    raise ValueError("open industry interval must be final")
                if previous.effective_to > current.effective_from:
                    raise ValueError("industry intervals cannot overlap")
        self.taxonomy = taxonomy
        self._memberships = ordered
        self._grouped = grouped

    @property
    def memberships(self) -> Tuple[IndustryMembership, ...]:
        return self._memberships

    def classification_as_of(
        self, security_id: SecurityId, as_of: date
    ) -> IndustryMembership:
        if type(as_of) is not date:
            raise TypeError("as_of must be a date, not a datetime")
        for membership in self._grouped.get(security_id, ()):
            if membership.contains(as_of):
                return membership
            if membership.effective_from > as_of:
                break
        raise UnknownIndustryHistoryError(
            f"no {self.taxonomy.name}/{self.taxonomy.version} classification "
            f"covers {security_id} at {as_of.isoformat()}"
        )
