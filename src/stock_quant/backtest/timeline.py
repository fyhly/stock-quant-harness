"""Stable event ordering with explicit decision/order/fill causality."""

from dataclasses import dataclass
from datetime import date
from enum import Enum, IntEnum
import re
from typing import Iterable, Optional, Tuple

from stock_quant.domain import TradingCalendar, TradingDay, UnknownTradingDayError


class EventPhase(IntEnum):
    PRE_MARKET_ACTIONS = 10
    OPEN_FILL = 20
    CLOSE_DECISION = 30
    POST_CLOSE_ORDER = 40
    CLOSE_VALUATION = 50
    RECORD_ENTITLEMENT = 60


class EventKind(str, Enum):
    CORPORATE_ACTION = "CORPORATE_ACTION"
    FILL = "FILL"
    DECISION = "DECISION"
    ORDER = "ORDER"
    VALUATION = "VALUATION"
    ENTITLEMENT = "ENTITLEMENT"


class TimelineConflictError(ValueError):
    """Raised when deterministic tie or causal rules are violated."""


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


@dataclass(frozen=True)
class TimelineEvent:
    event_id: str
    trading_day: TradingDay
    phase: EventPhase
    sequence: int
    kind: EventKind
    decision_date: Optional[date] = None

    def __post_init__(self) -> None:
        if not _SAFE_ID.fullmatch(self.event_id):
            raise ValueError("invalid timeline event_id")
        if not isinstance(self.trading_day, TradingDay):
            raise TypeError("trading_day must be TradingDay")
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError("sequence must be a nonnegative integer")
        expected = {
            EventKind.CORPORATE_ACTION: EventPhase.PRE_MARKET_ACTIONS,
            EventKind.FILL: EventPhase.OPEN_FILL,
            EventKind.DECISION: EventPhase.CLOSE_DECISION,
            EventKind.ORDER: EventPhase.POST_CLOSE_ORDER,
            EventKind.VALUATION: EventPhase.CLOSE_VALUATION,
            EventKind.ENTITLEMENT: EventPhase.RECORD_ENTITLEMENT,
        }[self.kind]
        if self.phase is not expected:
            raise ValueError(f"{self.kind.value} must use phase {expected.name}")
        if self.kind in (EventKind.ORDER, EventKind.FILL):
            if type(self.decision_date) is not date:
                raise ValueError("order/fill events require decision_date")
            if self.kind is EventKind.ORDER and self.trading_day.value != self.decision_date:
                raise TimelineConflictError("order must follow its same-day close decision")
            if self.kind is EventKind.FILL and self.trading_day.value <= self.decision_date:
                raise TimelineConflictError("fill must occur after its decision date")
        elif self.decision_date is not None:
            raise ValueError("decision_date is only valid for order/fill events")


class DeterministicTimeline:
    def __init__(
        self, calendar: TradingCalendar, events: Iterable[TimelineEvent]
    ) -> None:
        supplied = tuple(events)
        keys = set()
        ids = set()
        for event in supplied:
            if not isinstance(event, TimelineEvent):
                raise TypeError("events must contain TimelineEvent")
            try:
                calendar.sessions_on(event.trading_day.value)
            except UnknownTradingDayError as exc:
                raise ValueError("timeline event date is not a supplied trading day") from exc
            key = (event.trading_day, event.phase, event.sequence)
            if key in keys:
                raise TimelineConflictError("two events share the same deterministic key")
            if event.event_id in ids:
                raise TimelineConflictError("duplicate timeline event_id")
            keys.add(key)
            ids.add(event.event_id)
        self.calendar = calendar
        self._events = tuple(
            sorted(
                supplied,
                key=lambda event: (
                    event.trading_day,
                    event.phase,
                    event.sequence,
                    event.event_id,
                ),
            )
        )

    def replay(self) -> Tuple[TimelineEvent, ...]:
        return self._events
