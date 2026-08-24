"""Deterministic offline A-share backtest primitives."""

from stock_quant.backtest.account import (
    AccountError,
    AccountState,
    AccountValuation,
    book_buy,
    book_sell,
    MissingValuationError,
    Position,
    PositionLot,
    RawMark,
    StaleValuationError,
    TradeAccountingEntry,
    value_account,
)
from stock_quant.backtest.constraints import (
    ConstraintDecision,
    OrderSide,
    RejectionCode,
    SuspensionConstraint,
)
from stock_quant.backtest.timeline import (
    DeterministicTimeline,
    EventKind,
    EventPhase,
    TimelineConflictError,
    TimelineEvent,
)
from stock_quant.backtest.limits import (
    evaluate_price_limit,
    fill_price_within_limits,
    PriceLimitBand,
    PriceLimitRule,
    PriceLimitSchedule,
)
from stock_quant.backtest.t1 import (
    credit_corporate_action_lot,
    require_sellable,
    sellable_quantity,
    T1SellabilityError,
)

__all__ = [
    "DeterministicTimeline",
    "AccountError",
    "AccountState",
    "AccountValuation",
    "book_buy",
    "book_sell",
    "credit_corporate_action_lot",
    "ConstraintDecision",
    "EventKind",
    "EventPhase",
    "evaluate_price_limit",
    "fill_price_within_limits",
    "MissingValuationError",
    "OrderSide",
    "Position",
    "PositionLot",
    "PriceLimitBand",
    "PriceLimitRule",
    "PriceLimitSchedule",
    "RawMark",
    "RejectionCode",
    "require_sellable",
    "sellable_quantity",
    "StaleValuationError",
    "SuspensionConstraint",
    "TimelineConflictError",
    "T1SellabilityError",
    "TimelineEvent",
    "TradeAccountingEntry",
    "value_account",
]
