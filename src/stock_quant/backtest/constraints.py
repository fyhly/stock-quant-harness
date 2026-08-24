"""Historical execution constraints, separate from valuation."""

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional

from stock_quant.domain import (
    SecurityId,
    TradeStatus,
    TradeStatusHistory,
    TradingDay,
    UnknownStatusError,
)


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class RejectionCode(str, Enum):
    SUSPENDED = "SUSPENDED"
    UNKNOWN_TRADE_STATUS = "UNKNOWN_TRADE_STATUS"
    PRICE_LIMIT = "PRICE_LIMIT"
    MISSING_PRICE_LIMIT_FACTS = "MISSING_PRICE_LIMIT_FACTS"
    T1_FROZEN = "T1_FROZEN"
    ZERO_VOLUME = "ZERO_VOLUME"
    PARTICIPATION_CAP = "PARTICIPATION_CAP"
    INSUFFICIENT_CASH = "INSUFFICIENT_CASH"
    INSUFFICIENT_QUANTITY = "INSUFFICIENT_QUANTITY"
    MISSING_RAW_BAR = "MISSING_RAW_BAR"
    INVALID_FILL_TIMING = "INVALID_FILL_TIMING"


@dataclass(frozen=True)
class ConstraintDecision:
    allowed: bool
    rejection: Optional[RejectionCode] = None
    message: str = ""

    def __post_init__(self) -> None:
        if self.allowed == (self.rejection is not None):
            raise ValueError("allowed has no rejection; rejected requires one")


class SuspensionConstraint:
    def __init__(self, histories: Mapping[SecurityId, TradeStatusHistory]) -> None:
        copied = dict(histories)
        if any(not isinstance(value, TradeStatusHistory) for value in copied.values()):
            raise TypeError("histories must contain TradeStatusHistory")
        self._histories = copied

    def evaluate(
        self, security_id: SecurityId, trading_day: TradingDay, side: OrderSide
    ) -> ConstraintDecision:
        if not isinstance(side, OrderSide):
            raise TypeError("side must be OrderSide")
        history = self._histories.get(security_id)
        if history is None:
            return ConstraintDecision(
                False,
                RejectionCode.UNKNOWN_TRADE_STATUS,
                "no historical trade-status series",
            )
        try:
            status = history.as_of(trading_day.value)
        except UnknownStatusError:
            return ConstraintDecision(
                False,
                RejectionCode.UNKNOWN_TRADE_STATUS,
                "no status fact covers execution date",
            )
        if status is TradeStatus.SUSPENDED:
            return ConstraintDecision(
                False, RejectionCode.SUSPENDED, "security is historically suspended"
            )
        return ConstraintDecision(True)
