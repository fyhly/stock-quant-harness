"""Injected historical trading calendar without holiday assumptions."""

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import date, time
from typing import Iterable, Mapping, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class TradingCalendarError(ValueError):
    """Base error for explicit calendar lookup failures."""


class CalendarRangeError(TradingCalendarError):
    """Raised when a query is outside the calendar's declared coverage."""


class UnknownTradingDayError(TradingCalendarError):
    """Raised when a covered date is explicitly not a supplied trading day."""


class CalendarBoundaryError(TradingCalendarError):
    """Raised when no previous or next trading day exists in coverage."""


@dataclass(frozen=True, order=True)
class TradingDay:
    """An exchange trading date, separate from a weekday assumption."""

    value: date

    def __post_init__(self) -> None:
        if type(self.value) is not date:
            raise TypeError("TradingDay.value must be a date, not a datetime")


@dataclass(frozen=True)
class TradingSession:
    """A named half-open exchange-local wall-clock interval ``[start, end)``."""

    name: str
    start: time
    end: time

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("session name cannot be empty")
        if self.start.tzinfo is not None or self.end.tzinfo is not None:
            raise ValueError("session times must be naive exchange-local wall times")
        if self.start >= self.end:
            raise ValueError("session start must be before session end")


class TradingCalendar:
    """Immutable historical calendar built entirely from supplied local facts.

    Missing dates inside the declared inclusive coverage interval are known
    non-trading dates. Dates outside it are unknown and fail explicitly.
    """

    def __init__(
        self,
        days: Mapping[TradingDay, Iterable[TradingSession]],
        *,
        coverage_start: date,
        coverage_end: date,
        timezone: str,
    ) -> None:
        if type(coverage_start) is not date or type(coverage_end) is not date:
            raise TypeError("calendar coverage bounds must be dates")
        if coverage_start > coverage_end:
            raise ValueError("coverage_start must not be after coverage_end")
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown calendar timezone: {timezone!r}") from exc

        normalized = {}
        for day, raw_sessions in days.items():
            if not isinstance(day, TradingDay):
                raise TypeError("calendar keys must be TradingDay instances")
            if not coverage_start <= day.value <= coverage_end:
                raise ValueError("supplied trading day is outside declared coverage")
            sessions = tuple(raw_sessions)
            self._validate_sessions(sessions)
            normalized[day] = sessions

        self._sessions = normalized
        self._ordered_days = tuple(sorted(normalized))
        self.coverage_start = coverage_start
        self.coverage_end = coverage_end
        self.timezone = timezone

    @property
    def trading_days(self) -> Tuple[TradingDay, ...]:
        return self._ordered_days

    def is_trading_day(self, value: date) -> bool:
        self._validate_query(value)
        return TradingDay(value) in self._sessions

    def sessions_on(self, value: date) -> Tuple[TradingSession, ...]:
        self._validate_query(value)
        try:
            return self._sessions[TradingDay(value)]
        except KeyError as exc:
            raise UnknownTradingDayError(
                f"{value.isoformat()} is not a supplied trading day"
            ) from exc

    def previous_trading_day(self, value: date) -> TradingDay:
        self._validate_query(value)
        index = bisect_left(self._ordered_days, TradingDay(value))
        if index == 0:
            raise CalendarBoundaryError("no previous trading day in coverage")
        return self._ordered_days[index - 1]

    def next_trading_day(self, value: date) -> TradingDay:
        self._validate_query(value)
        index = bisect_right(self._ordered_days, TradingDay(value))
        if index == len(self._ordered_days):
            raise CalendarBoundaryError("no next trading day in coverage")
        return self._ordered_days[index]

    def _validate_query(self, value: date) -> None:
        if type(value) is not date:
            raise TypeError("calendar queries require a date, not a datetime")
        if not self.coverage_start <= value <= self.coverage_end:
            raise CalendarRangeError(
                f"{value.isoformat()} is outside calendar coverage "
                f"[{self.coverage_start.isoformat()}, "
                f"{self.coverage_end.isoformat()}]"
            )

    @staticmethod
    def _validate_sessions(sessions: Tuple[TradingSession, ...]) -> None:
        if not sessions:
            raise ValueError("a trading day must contain at least one session")
        if any(not isinstance(session, TradingSession) for session in sessions):
            raise TypeError("sessions must be TradingSession instances")
        for previous, current in zip(sessions, sessions[1:]):
            if previous.start >= current.start:
                raise ValueError("sessions must be ordered by start time")
            if previous.end > current.start:
                raise ValueError("trading sessions cannot overlap")
