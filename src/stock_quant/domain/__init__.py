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
from stock_quant.domain.status import (
    StatusHistoryError,
    StatusInterval,
    STStatus,
    STStatusHistory,
    TradeStatus,
    TradeStatusHistory,
    UnknownStatusError,
)

__all__ = [
    "CalendarBoundaryError",
    "CalendarRangeError",
    "Exchange",
    "ListingLifecycle",
    "ListingStatus",
    "MarketSegment",
    "SecurityId",
    "StatusHistoryError",
    "StatusInterval",
    "STStatus",
    "STStatusHistory",
    "TradingCalendar",
    "TradingCalendarError",
    "TradingDay",
    "TradingSession",
    "TradeStatus",
    "TradeStatusHistory",
    "UnknownTradingDayError",
    "UnknownStatusError",
]
