from datetime import date
from pathlib import Path

from stock_quant.backtest import verify_backtest_result
from stock_quant.domain import TradingDay
from stock_quant.e2e import run_real_backtest


ROOT = Path(__file__).parents[1] / "fixtures" / "real" / "v1"
DAY = TradingDay(date(2024, 11, 29))


def test_real_backtest_repeats_exact_fingerprint_without_future_fill() -> None:
    first = run_real_backtest(ROOT, DAY)
    assert first == run_real_backtest(ROOT, DAY)
    assert all(fill.trading_day > DAY for fill in first.fills)
    verify_backtest_result(first)


def test_real_backtest_accounting_and_expected_outputs_are_frozen() -> None:
    result = run_real_backtest(ROOT, DAY)
    assert len(result.fills) == len(result.trade_ledger) == 1
    assert (
        result.fingerprint
        == "b6b4be7b4917c65f6ba03cca6a4a1f231266034dbc39803a80dfa3fc2fca1e96"
    )
    assert result.fills[0].raw_open == result.fills[0].price
    assert result.fills[0].quantity == 7000
    assert (
        result.equity[0].equity
        == result.holdings[0].cash + result.holdings[0].positions[0][2]
    )
    assert result.holdings[0].cash >= 0 and result.equity[0].equity > 0
