from datetime import date, datetime, time

import pytest

from stock_quant.domain import (
    CalendarBoundaryError,
    CalendarRangeError,
    TradingCalendar,
    TradingDay,
    TradingSession,
    UnknownTradingDayError,
)


MORNING = TradingSession("morning", time(9, 30), time(11, 30))
AFTERNOON = TradingSession("afternoon", time(13), time(15))


@pytest.fixture
def calendar() -> TradingCalendar:
    sessions = (MORNING, AFTERNOON)
    return TradingCalendar(
        {
            TradingDay(date(2024, 10, 8)): sessions,
            TradingDay(date(2024, 10, 9)): sessions,
            TradingDay(date(2024, 10, 11)): sessions,
        },
        coverage_start=date(2024, 10, 1),
        coverage_end=date(2024, 10, 13),
        timezone="Asia/Shanghai",
    )


def test_supplied_history_not_weekdays_is_authoritative(
    calendar: TradingCalendar,
) -> None:
    assert not calendar.is_trading_day(date(2024, 10, 7))  # supplied holiday
    assert not calendar.is_trading_day(date(2024, 10, 12))  # weekend
    assert calendar.is_trading_day(date(2024, 10, 8))


def test_sessions_and_order_are_deterministic(calendar: TradingCalendar) -> None:
    assert calendar.trading_days == (
        TradingDay(date(2024, 10, 8)),
        TradingDay(date(2024, 10, 9)),
        TradingDay(date(2024, 10, 11)),
    )
    assert calendar.sessions_on(date(2024, 10, 8)) == (MORNING, AFTERNOON)


def test_previous_and_next_work_across_holiday_gap(
    calendar: TradingCalendar,
) -> None:
    assert calendar.previous_trading_day(date(2024, 10, 10)) == TradingDay(
        date(2024, 10, 9)
    )
    assert calendar.next_trading_day(date(2024, 10, 10)) == TradingDay(
        date(2024, 10, 11)
    )


def test_unknown_non_trading_day_fails_explicitly(calendar: TradingCalendar) -> None:
    with pytest.raises(UnknownTradingDayError):
        calendar.sessions_on(date(2024, 10, 10))


def test_out_of_range_and_boundaries_fail_explicitly(
    calendar: TradingCalendar,
) -> None:
    with pytest.raises(CalendarRangeError):
        calendar.is_trading_day(date(2024, 9, 30))
    with pytest.raises(CalendarBoundaryError):
        calendar.previous_trading_day(date(2024, 10, 8))
    with pytest.raises(CalendarBoundaryError):
        calendar.next_trading_day(date(2024, 10, 11))


def test_invalid_calendar_and_session_facts_are_rejected() -> None:
    with pytest.raises(ValueError, match="overlap"):
        TradingCalendar(
            {
                TradingDay(date(2024, 1, 2)): (
                    MORNING,
                    TradingSession("overlap", time(11), time(12)),
                )
            },
            coverage_start=date(2024, 1, 1),
            coverage_end=date(2024, 1, 2),
            timezone="Asia/Shanghai",
        )
    with pytest.raises(ValueError, match="at least one"):
        TradingCalendar(
            {TradingDay(date(2024, 1, 2)): ()},
            coverage_start=date(2024, 1, 1),
            coverage_end=date(2024, 1, 2),
            timezone="Asia/Shanghai",
        )


def test_datetime_cannot_silently_become_a_trading_date() -> None:
    with pytest.raises(TypeError):
        TradingDay(datetime(2024, 1, 2, 9, 30))
