"""Versioned, unadjusted A-share daily bar schema."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Tuple

from stock_quant.domain import SecurityId, TradingDay


DAILY_BAR_SCHEMA_VERSION = "daily-bar-v1"


@dataclass(frozen=True)
class DailyBar:
    """An immutable unadjusted OHLCV observation for one trading date."""

    security_id: SecurityId
    trading_day: TradingDay
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    amount: Decimal
    schema_version: str = DAILY_BAR_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.security_id, SecurityId):
            raise TypeError("security_id must be a SecurityId")
        if not isinstance(self.trading_day, TradingDay):
            raise TypeError("trading_day must be a TradingDay")
        if self.schema_version != DAILY_BAR_SCHEMA_VERSION:
            raise ValueError(f"unsupported DailyBar schema: {self.schema_version!r}")
        prices = {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }
        for name, value in prices.items():
            self._validate_decimal(name, value, positive=True)
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be at least open, close, and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be at most open, close, and high")
        if type(self.volume) is not int:
            raise TypeError("volume must be an integer")
        if self.volume < 0:
            raise ValueError("volume cannot be negative")
        self._validate_decimal("amount", self.amount, positive=False)

    @staticmethod
    def _validate_decimal(name: str, value: Decimal, *, positive: bool) -> None:
        if not isinstance(value, Decimal):
            raise TypeError(f"{name} must be a Decimal")
        if not value.is_finite():
            raise ValueError(f"{name} must be finite")
        if positive and value <= 0:
            raise ValueError(f"{name} must be positive")
        if not positive and value < 0:
            raise ValueError(f"{name} cannot be negative")


@dataclass(frozen=True)
class DailyBarSeries:
    """A single-security series whose input must already be strictly ordered."""

    security_id: SecurityId
    bars: Tuple[DailyBar, ...]
    schema_version: str = DAILY_BAR_SCHEMA_VERSION

    def __init__(
        self,
        security_id: SecurityId,
        bars: Iterable[DailyBar],
        schema_version: str = DAILY_BAR_SCHEMA_VERSION,
    ) -> None:
        object.__setattr__(self, "security_id", security_id)
        object.__setattr__(self, "bars", tuple(bars))
        object.__setattr__(self, "schema_version", schema_version)
        self.__post_init__()

    def __post_init__(self) -> None:
        if not isinstance(self.security_id, SecurityId):
            raise TypeError("security_id must be a SecurityId")
        if self.schema_version != DAILY_BAR_SCHEMA_VERSION:
            raise ValueError(f"unsupported DailyBar schema: {self.schema_version!r}")
        previous = None
        for bar in self.bars:
            if not isinstance(bar, DailyBar):
                raise TypeError("bars must contain DailyBar instances")
            if bar.security_id != self.security_id:
                raise ValueError("all bars must belong to the series security_id")
            if bar.schema_version != self.schema_version:
                raise ValueError("bar and series schema versions must match")
            if previous is not None and bar.trading_day <= previous:
                raise ValueError("bar trading dates must be unique and strictly ordered")
            previous = bar.trading_day
