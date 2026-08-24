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
from stock_quant.domain.listing import ListingLifecycle, ListingStatus
from stock_quant.domain.security import Exchange, MarketSegment, SecurityId

__all__ = [
    "CalendarBoundaryError",
    "CalendarRangeError",
    "Exchange",
    "ListingLifecycle",
    "ListingStatus",
    "MarketSegment",
    "SecurityId",
    "TradingCalendar",
    "TradingCalendarError",
    "TradingDay",
    "TradingSession",
    "UnknownTradingDayError",
]
