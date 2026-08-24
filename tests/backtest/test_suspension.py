from datetime import date
from decimal import Decimal

from stock_quant.backtest import (
    AccountState,
    book_buy,
    OrderSide,
    RawMark,
    RejectionCode,
    SuspensionConstraint,
    value_account,
)
from stock_quant.domain import (
    Exchange,
    SecurityId,
    StatusInterval,
    TradeStatus,
    TradeStatusHistory,
    TradingDay,
)


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
D1 = TradingDay(date(2024, 1, 2))
D2 = TradingDay(date(2024, 1, 3))


def constraint() -> SuspensionConstraint:
    return SuspensionConstraint(
        {
            SECURITY: TradeStatusHistory(
                [
                    StatusInterval(TradeStatus.TRADING, D1.value, D2.value),
                    StatusInterval(TradeStatus.SUSPENDED, D2.value),
                ]
            )
        }
    )


def test_suspended_buy_and_sell_are_rejected() -> None:
    for side in OrderSide:
        decision = constraint().evaluate(SECURITY, D2, side)
        assert not decision.allowed
        assert decision.rejection is RejectionCode.SUSPENDED
    assert constraint().evaluate(SECURITY, D1, OrderSide.BUY).allowed


def test_unknown_history_fails_closed() -> None:
    decision = SuspensionConstraint({}).evaluate(SECURITY, D1, OrderSide.BUY)

    assert decision.rejection is RejectionCode.UNKNOWN_TRADE_STATUS


def test_suspension_does_not_block_separate_raw_valuation() -> None:
    state = book_buy(
        AccountState(Decimal("10000")), SECURITY, D1,
        quantity=100, price=Decimal("10")
    )

    assert not constraint().evaluate(SECURITY, D2, OrderSide.SELL).allowed
    assert value_account(
        state, D2, {SECURITY: RawMark(SECURITY, D2, Decimal("9"))}
    ).equity == Decimal("9900")
