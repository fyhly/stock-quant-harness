from dataclasses import replace
from datetime import date, time
from decimal import Decimal

import pytest

from stock_quant.actions import RawExecutionBar, RawExecutionPriceView
from stock_quant.backtest import (
    AccountState,
    BacktestResult,
    create_backtest_result,
    EquityPoint,
    execute_next_open,
    HoldingSnapshot,
    OrderIntent,
    OrderSide,
    PriceLimitRule,
    PriceLimitSchedule,
    RawMark,
    RejectionCode,
    RejectionRecord,
    ReplayIdentityError,
    SlippageModel,
    SuspensionConstraint,
    TradingCostRule,
    TradingCostSchedule,
    value_account,
    verify_backtest_result,
)
from stock_quant.domain import (
    Exchange,
    MarketSegment,
    SecurityId,
    StatusInterval,
    STStatus,
    TradeStatus,
    TradeStatusHistory,
    TradingCalendar,
    TradingDay,
    TradingSession,
)


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
D1 = TradingDay(date(2024, 1, 2))
D2 = TradingDay(date(2024, 1, 3))
D3 = TradingDay(date(2024, 1, 4))
IDENTITY = "a" * 64


def run_scenario() -> BacktestResult:
    session = TradingSession("day", time(9, 30), time(15))
    calendar = TradingCalendar(
        {D1: (session,), D2: (session,), D3: (session,)},
        coverage_start=D1.value,
        coverage_end=D3.value,
        timezone="Asia/Shanghai",
    )
    histories = {
        SECURITY: TradeStatusHistory(
            [
                StatusInterval(TradeStatus.TRADING, D1.value, D3.value),
                StatusInterval(TradeStatus.SUSPENDED, D3.value),
            ]
        )
    }
    limits = PriceLimitSchedule(
        "limits-v1",
        [
            PriceLimitRule(
                MarketSegment.MAIN_BOARD,
                date(2000, 1, 1),
                None,
                Decimal("0.1"),
            )
        ],
    )
    costs = TradingCostSchedule(
        "cost-v1",
        [
            TradingCostRule(
                date(2000, 1, 1),
                None,
                Decimal("0.0003"),
                Decimal("5"),
                Decimal(0),
                Decimal(0),
                Decimal("0.0005"),
            )
        ],
    )
    buy = OrderIntent("buy-1", SECURITY, OrderSide.BUY, 500, D1, D2)
    buy_bar = RawExecutionBar(
        SECURITY,
        D2,
        Decimal("10"),
        Decimal("10.2"),
        Decimal("9.8"),
        Decimal("10"),
        1000,
        Decimal("10000"),
        "daily-bar-v1",
    )
    bought = execute_next_open(
        buy,
        view=RawExecutionPriceView(SECURITY, (buy_bar,)),
        account=AccountState(Decimal("10000")),
        calendar=calendar,
        suspension=SuspensionConstraint(histories),
        price_limits=limits,
        prior_close=Decimal("10"),
        st_status=STStatus.NORMAL,
        costs=costs,
        slippage=SlippageModel("slip-v1", Decimal("100")),
        participation_cap=Decimal("0.25"),
    )
    assert bought.fill is not None

    sell = OrderIntent("sell-1", SECURITY, OrderSide.SELL, 200, D2, D3)
    sell_bar = replace(
        buy_bar,
        trading_day=D3,
        open=Decimal("9"),
        high=Decimal("9.2"),
        low=Decimal("8.8"),
        close=Decimal("9"),
    )
    rejected = execute_next_open(
        sell,
        view=RawExecutionPriceView(SECURITY, (sell_bar,)),
        account=bought.account,
        calendar=calendar,
        suspension=SuspensionConstraint(histories),
        price_limits=limits,
        prior_close=Decimal("10"),
        st_status=STStatus.NORMAL,
        costs=costs,
        slippage=SlippageModel("slip-v1", Decimal("100")),
        participation_cap=Decimal("0.25"),
    )
    assert rejected.rejection is RejectionCode.SUSPENDED
    valuation = value_account(
        rejected.account,
        D3,
        {SECURITY: RawMark(SECURITY, D3, Decimal("9"))},
    )
    return create_backtest_result(
        fills=(bought.fill,),
        rejections=(RejectionRecord("sell-1", D3, rejected.rejection),),
        holdings=(HoldingSnapshot.from_account(D3, rejected.account),),
        equity=(EquityPoint(D3, valuation.equity),),
        trade_ledger=rejected.account.ledger,
        action_ledger_keys=("action-1:record", "action-1:pay"),
        config_identity=IDENTITY,
        data_identity="b" * 64,
        code_identity="c" * 64,
    )


def test_complete_result_is_exactly_repeatable_and_auditable() -> None:
    first = run_scenario()
    second = run_scenario()

    assert first == second
    assert first.fingerprint == second.fingerprint
    assert len(first.fills) == len(first.rejections) == 1
    assert first.holdings[0].positions[0][1] == 200
    assert first.equity[0].equity == Decimal("9775")
    assert first.trade_ledger == second.trade_ledger
    assert first.action_ledger_keys == ("action-1:record", "action-1:pay")
    verify_backtest_result(first)


def test_tamper_and_invalid_replay_identities_fail_closed() -> None:
    result = run_scenario()
    changed_equity = replace(
        result,
        equity=(EquityPoint(D3, result.equity[0].equity + Decimal("0.01")),),
    )

    with pytest.raises(ReplayIdentityError, match="fingerprint mismatch"):
        verify_backtest_result(changed_equity)
    with pytest.raises(ReplayIdentityError, match="data_identity"):
        verify_backtest_result(replace(result, data_identity="../data"))
