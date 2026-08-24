"""Injected-calendar close decisions with next-session eligibility."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Tuple
from zoneinfo import ZoneInfo

from stock_quant.domain import TradingCalendar, TradingDay
from stock_quant.strategy.api import StrategyContractError


class RebalanceFrequency(str, Enum):
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


@dataclass(frozen=True)
class ScheduledDecision:
    decision_day: TradingDay
    decision_cutoff: datetime
    order_eligible_day: TradingDay


def rebalance_schedule(
    calendar: TradingCalendar,
    *,
    start: TradingDay,
    end: TradingDay,
    frequency: RebalanceFrequency,
) -> Tuple[ScheduledDecision, ...]:
    if start > end:
        raise StrategyContractError("schedule start must not follow end")
    days = calendar.trading_days
    if start not in days or end not in days:
        raise StrategyContractError("schedule bounds must be supplied trading days")
    output = []
    for index, day in enumerate(days[:-1]):
        if not start <= day <= end:
            continue
        next_day = days[index + 1]
        boundary = (
            day.value.isocalendar()[:2] != next_day.value.isocalendar()[:2]
            if frequency is RebalanceFrequency.WEEKLY
            else (day.value.year, day.value.month)
            != (next_day.value.year, next_day.value.month)
        )
        if boundary:
            sessions = calendar.sessions_on(day.value)
            cutoff = datetime.combine(
                day.value, sessions[-1].end, ZoneInfo(calendar.timezone)
            )
            output.append(ScheduledDecision(day, cutoff, next_day))
    return tuple(output)
