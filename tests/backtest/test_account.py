from datetime import date
from decimal import Decimal

import pytest

from stock_quant.backtest import (
    AccountError,
    AccountState,
    book_buy,
    book_sell,
    MissingValuationError,
    RawMark,
    StaleValuationError,
    value_account,
)
from stock_quant.domain import Exchange, SecurityId, TradingDay


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
D1 = TradingDay(date(2024, 1, 2))
D2 = TradingDay(date(2024, 1, 3))


def test_buy_sell_fifo_cost_cash_and_realized_pnl() -> None:
    state = AccountState(Decimal("10000"))
    state = book_buy(state, SECURITY, D1, quantity=100, price=Decimal("10"))
    state = book_buy(state, SECURITY, D2, quantity=100, price=Decimal("12"))
    state = book_sell(state, SECURITY, D2, quantity=150, price=Decimal("15"))

    assert state.cash == Decimal("10050")
    assert state.position(SECURITY).quantity == 50
    assert state.position(SECURITY).total_cost == Decimal("600")
    assert state.ledger[-1].realized_pnl == Decimal("650")


def test_equity_is_cash_plus_raw_market_value() -> None:
    state = book_buy(
        AccountState(Decimal("10000")), SECURITY, D1,
        quantity=100, price=Decimal("10")
    )
    valuation = value_account(
        state, D1, {SECURITY: RawMark(SECURITY, D1, Decimal("11"))}
    )

    assert valuation.cash == Decimal("9000")
    assert valuation.market_value == Decimal("1100")
    assert valuation.equity == Decimal("10100")


def test_missing_and_stale_marks_fail_closed() -> None:
    state = book_buy(
        AccountState(Decimal("10000")), SECURITY, D1,
        quantity=100, price=Decimal("10")
    )
    with pytest.raises(MissingValuationError):
        value_account(state, D2, {})
    with pytest.raises(StaleValuationError):
        value_account(state, D2, {SECURITY: RawMark(SECURITY, D1, Decimal("11"))})


def test_cash_and_quantity_constraints_fail() -> None:
    with pytest.raises(AccountError, match="cash"):
        book_buy(
            AccountState(Decimal("100")), SECURITY, D1,
            quantity=100, price=Decimal("10")
        )
    with pytest.raises(AccountError, match="quantity"):
        book_sell(
            AccountState(Decimal("100")), SECURITY, D1,
            quantity=1, price=Decimal("10")
        )
