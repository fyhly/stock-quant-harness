"""Effective-dated historical ST and trading statuses."""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Generic, Iterable, Optional, Tuple, Type, TypeVar


class STStatus(str, Enum):
    """A-share special-treatment state."""

    NORMAL = "NORMAL"
    ST = "ST"
    STAR_ST = "STAR_ST"


class TradeStatus(str, Enum):
    """Exchange-published ability-to-trade state, not fill semantics."""

    TRADING = "TRADING"
    SUSPENDED = "SUSPENDED"


StatusT = TypeVar("StatusT", bound=Enum)


class StatusHistoryError(ValueError):
    """Base error for invalid or unknown status history."""


class UnknownStatusError(StatusHistoryError):
    """Raised when no supplied fact covers the requested as-of date."""


@dataclass(frozen=True)
class StatusInterval(Generic[StatusT]):
    """A status fact effective on ``[effective_from, effective_to)``."""

    value: StatusT
    effective_from: date
    effective_to: Optional[date] = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, Enum):
            raise TypeError("status value must be an Enum")
        if type(self.effective_from) is not date:
            raise TypeError("effective_from must be a date, not a datetime")
        if self.effective_to is not None:
            if type(self.effective_to) is not date:
                raise TypeError("effective_to must be a date, not a datetime")
            if self.effective_to <= self.effective_from:
                raise ValueError("effective_to must be after effective_from")

    def contains(self, as_of: date) -> bool:
        if type(as_of) is not date:
            raise TypeError("as_of must be a date, not a datetime")
        return self.effective_from <= as_of and (
            self.effective_to is None or as_of < self.effective_to
        )


class _StatusHistory(Generic[StatusT]):
    def __init__(
        self,
        intervals: Iterable[StatusInterval[StatusT]],
        status_type: Type[StatusT],
    ) -> None:
        ordered = tuple(sorted(intervals, key=lambda interval: interval.effective_from))
        if not ordered:
            raise ValueError("status history must contain at least one interval")
        for interval in ordered:
            if not isinstance(interval, StatusInterval):
                raise TypeError("history entries must be StatusInterval instances")
            if not isinstance(interval.value, status_type):
                raise TypeError(f"status value must be {status_type.__name__}")
        for previous, current in zip(ordered, ordered[1:]):
            if previous.effective_to is None:
                raise ValueError("an open-ended interval must be the final interval")
            if previous.effective_to > current.effective_from:
                raise ValueError("status intervals cannot overlap")
        self._intervals = ordered

    @property
    def intervals(self) -> Tuple[StatusInterval[StatusT], ...]:
        return self._intervals

    def as_of(self, as_of: date) -> StatusT:
        if type(as_of) is not date:
            raise TypeError("as_of must be a date, not a datetime")
        for interval in self._intervals:
            if interval.contains(as_of):
                return interval.value
            if interval.effective_from > as_of:
                break
        raise UnknownStatusError(
            f"no supplied status fact covers {as_of.isoformat()}"
        )


class STStatusHistory(_StatusHistory[STStatus]):
    """Immutable, gap-preserving point-in-time ST status history."""

    def __init__(self, intervals: Iterable[StatusInterval[STStatus]]) -> None:
        super().__init__(intervals, STStatus)


class TradeStatusHistory(_StatusHistory[TradeStatus]):
    """Immutable, gap-preserving point-in-time trade status history."""

    def __init__(self, intervals: Iterable[StatusInterval[TradeStatus]]) -> None:
        super().__init__(intervals, TradeStatus)
