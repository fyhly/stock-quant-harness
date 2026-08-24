"""Provider-independent A-share domain primitives."""

from stock_quant.domain.calendar import (
    CalendarBoundaryError,
    CalendarRangeError,
    TradingCalendar,
    TradingCalendarError,
    TradingDay,
    TradingSession,
    UnknownTradingDayError,
)
from stock_quant.domain.security import Exchange, MarketSegment, SecurityId

__all__ = [
    "CalendarBoundaryError",
    "CalendarRangeError",
    "Exchange",
    "MarketSegment",
    "SecurityId",
    "TradingCalendar",
    "TradingCalendarError",
    "TradingDay",
    "TradingSession",
    "UnknownTradingDayError",
]
