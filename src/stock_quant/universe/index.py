"""Immutable point-in-time index membership history."""

from dataclasses import dataclass
from datetime import date
import re
from typing import Dict, Iterable, Optional, Tuple

from stock_quant.domain import SecurityId


class UnknownIndexHistoryError(ValueError):
    """Raised when a query falls outside declared complete history coverage."""


@dataclass(frozen=True, order=True)
class IndexId:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", self.value
        ):
            raise ValueError("invalid index identifier")


@dataclass(frozen=True)
class IndexMembership:
    """Membership effective on ``[effective_from, effective_to)``."""

    index_id: IndexId
    security_id: SecurityId
    effective_from: date
    effective_to: Optional[date] = None

    def __post_init__(self) -> None:
        if not isinstance(self.index_id, IndexId):
            raise TypeError("index_id must be an IndexId")
        if not isinstance(self.security_id, SecurityId):
            raise TypeError("security_id must be a SecurityId")
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


class IndexMembershipHistory:
    """Complete membership facts inside an explicit inclusive coverage range."""

    def __init__(
        self,
        index_id: IndexId,
        memberships: Iterable[IndexMembership],
        *,
        coverage_start: date,
        coverage_end: date,
    ) -> None:
        if type(coverage_start) is not date or type(coverage_end) is not date:
            raise TypeError("coverage bounds must be dates")
        if coverage_start > coverage_end:
            raise ValueError("coverage_start must not be after coverage_end")
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
        grouped: Dict[SecurityId, list[IndexMembership]] = {}
        for membership in ordered:
            if not isinstance(membership, IndexMembership):
                raise TypeError("memberships must contain IndexMembership")
            if membership.index_id != index_id:
                raise ValueError("membership index identity mismatch")
            grouped.setdefault(membership.security_id, []).append(membership)
        for intervals in grouped.values():
            for previous, current in zip(intervals, intervals[1:]):
                if previous.effective_to is None:
                    raise ValueError("open membership interval must be final")
                if previous.effective_to > current.effective_from:
                    raise ValueError("index membership intervals cannot overlap")
        self.index_id = index_id
        self.coverage_start = coverage_start
        self.coverage_end = coverage_end
        self._memberships = ordered
        self._grouped = grouped

    @property
    def memberships(self) -> Tuple[IndexMembership, ...]:
        return self._memberships

    def is_member(self, security_id: SecurityId, as_of: date) -> bool:
        self._validate_as_of(as_of)
        return any(
            interval.contains(as_of) for interval in self._grouped.get(security_id, ())
        )

    def members_as_of(self, as_of: date) -> Tuple[SecurityId, ...]:
        self._validate_as_of(as_of)
        return tuple(
            sorted(
                security_id
                for security_id, intervals in self._grouped.items()
                if any(interval.contains(as_of) for interval in intervals)
            )
        )

    def _validate_as_of(self, as_of: date) -> None:
        if type(as_of) is not date:
            raise TypeError("as_of must be a date, not a datetime")
        if not self.coverage_start <= as_of <= self.coverage_end:
            raise UnknownIndexHistoryError(
                "as-of date is outside complete index-history coverage"
            )
