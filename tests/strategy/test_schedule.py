from datetime import date, time

from stock_quant.domain import TradingCalendar, TradingDay, TradingSession
from stock_quant.strategy import rebalance_schedule, RebalanceFrequency


def calendar() -> TradingCalendar:
    raw = (
        date(2024, 1, 30),
        date(2024, 1, 31),
        date(2024, 2, 2),
        date(2024, 2, 5),
        date(2024, 2, 9),
        date(2024, 2, 19),
    )
    session = TradingSession("day", time(9, 30), time(15))
    return TradingCalendar(
        {TradingDay(day): (session,) for day in raw},
        coverage_start=raw[0],
        coverage_end=raw[-1],
        timezone="Asia/Shanghai",
    )


def test_week_and_month_boundaries_use_only_injected_days() -> None:
    source = calendar()
    weekly = rebalance_schedule(
        source,
        start=source.trading_days[0],
        end=source.trading_days[-1],
        frequency=RebalanceFrequency.WEEKLY,
    )
    monthly = rebalance_schedule(
        source,
        start=source.trading_days[0],
        end=source.trading_days[-1],
        frequency=RebalanceFrequency.MONTHLY,
    )
    assert tuple(item.decision_day.value for item in weekly) == (
        date(2024, 2, 2),
        date(2024, 2, 9),
    )
    assert tuple(item.decision_day.value for item in monthly) == (date(2024, 1, 31),)


def test_close_cutoff_and_next_session_prevent_same_day_price() -> None:
    source = calendar()
    item = rebalance_schedule(
        source,
        start=source.trading_days[0],
        end=source.trading_days[-1],
        frequency=RebalanceFrequency.MONTHLY,
    )[0]
    assert item.decision_cutoff.hour == 15
    assert item.order_eligible_day.value == date(2024, 2, 2)
    assert item.order_eligible_day > item.decision_day
