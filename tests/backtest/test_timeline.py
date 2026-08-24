from datetime import date, time

import pytest

from stock_quant.backtest import (
    DeterministicTimeline,
    EventKind,
    EventPhase,
    TimelineConflictError,
    TimelineEvent,
)
from stock_quant.domain import TradingCalendar, TradingDay, TradingSession


D1 = TradingDay(date(2024, 1, 2))
D2 = TradingDay(date(2024, 1, 3))


def calendar() -> TradingCalendar:
    session = TradingSession("day", time(9, 30), time(15))
    return TradingCalendar(
        {D1: (session,), D2: (session,)},
        coverage_start=date(2024, 1, 1),
        coverage_end=date(2024, 1, 7),
        timezone="Asia/Shanghai",
    )


def events() -> tuple[TimelineEvent, ...]:
    return (
        TimelineEvent("decision", D1, EventPhase.CLOSE_DECISION, 0, EventKind.DECISION),
        TimelineEvent(
            "order", D1, EventPhase.POST_CLOSE_ORDER, 0, EventKind.ORDER, D1.value
        ),
        TimelineEvent("valuation", D1, EventPhase.CLOSE_VALUATION, 0, EventKind.VALUATION),
        TimelineEvent(
            "entitlement", D1, EventPhase.RECORD_ENTITLEMENT, 0, EventKind.ENTITLEMENT
        ),
        TimelineEvent("fill", D2, EventPhase.OPEN_FILL, 0, EventKind.FILL, D1.value),
    )


def test_input_order_invariance_phase_order_and_replay() -> None:
    forward = DeterministicTimeline(calendar(), events()).replay()
    reverse = DeterministicTimeline(calendar(), reversed(events())).replay()

    assert forward == reverse
    assert [event.event_id for event in forward] == [
        "decision", "order", "valuation", "entitlement", "fill"
    ]
    assert DeterministicTimeline(calendar(), forward).replay() == forward


def test_same_key_conflict_is_rejected_not_insertion_tied() -> None:
    duplicate_key = TimelineEvent(
        "other-decision", D1, EventPhase.CLOSE_DECISION, 0, EventKind.DECISION
    )
    with pytest.raises(TimelineConflictError, match="same deterministic key"):
        DeterministicTimeline(calendar(), [events()[0], duplicate_key])


def test_same_day_or_future_decision_fill_is_rejected() -> None:
    with pytest.raises(TimelineConflictError, match="after"):
        TimelineEvent("fill", D1, EventPhase.OPEN_FILL, 0, EventKind.FILL, D1.value)
    with pytest.raises(TimelineConflictError, match="after"):
        TimelineEvent("fill", D1, EventPhase.OPEN_FILL, 0, EventKind.FILL, D2.value)


def test_invalid_calendar_day_and_phase_are_rejected() -> None:
    weekend = TimelineEvent(
        "weekend", TradingDay(date(2024, 1, 6)), EventPhase.CLOSE_DECISION,
        0, EventKind.DECISION
    )
    with pytest.raises(ValueError, match="not a supplied trading day"):
        DeterministicTimeline(calendar(), [weekend])
    with pytest.raises(ValueError, match="must use phase"):
        TimelineEvent("wrong", D1, EventPhase.OPEN_FILL, 0, EventKind.DECISION)
