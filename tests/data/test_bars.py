from datetime import date
from decimal import Decimal

import pytest

from stock_quant.data import DailyBar, DailyBarSeries
from stock_quant.domain import Exchange, SecurityId, TradingDay


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
OTHER = SecurityId("000001", Exchange.SHENZHEN)


def bar(day: int = 2, **overrides: object) -> DailyBar:
    values = {
        "security_id": SECURITY,
        "trading_day": TradingDay(date(2024, 1, day)),
        "open": Decimal("10.00"),
        "high": Decimal("11.00"),
        "low": Decimal("9.50"),
        "close": Decimal("10.50"),
        "volume": 1000,
        "amount": Decimal("10250.00"),
    }
    values.update(overrides)
    return DailyBar(**values)  # type: ignore[arg-type]


def test_valid_unadjusted_bar_and_immutable_series() -> None:
    first = bar(2)
    second = bar(3)
    series = DailyBarSeries(SECURITY, [first, second])

    assert series.bars == (first, second)
    assert series.schema_version == "daily-bar-v1"
    with pytest.raises(AttributeError):
        first.close = Decimal("1")  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("high", Decimal("10.49")),
        ("low", Decimal("10.01")),
        ("open", Decimal("0")),
        ("close", Decimal("NaN")),
    ],
)
def test_ohlc_invariants_fail_explicitly(field: str, value: Decimal) -> None:
    with pytest.raises(ValueError):
        bar(**{field: value})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [("volume", -1), ("amount", Decimal("-0.01"))],
)
def test_negative_volume_or_amount_is_rejected(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        bar(**{field: value})  # type: ignore[arg-type]


def test_float_price_and_boolean_volume_are_rejected() -> None:
    with pytest.raises(TypeError, match="Decimal"):
        bar(open=10.0)
    with pytest.raises(TypeError, match="integer"):
        bar(volume=True)


def test_duplicate_and_out_of_order_dates_are_rejected() -> None:
    with pytest.raises(ValueError, match="strictly ordered"):
        DailyBarSeries(SECURITY, [bar(2), bar(2)])
    with pytest.raises(ValueError, match="strictly ordered"):
        DailyBarSeries(SECURITY, [bar(3), bar(2)])


def test_mixed_security_and_schema_versions_are_rejected() -> None:
    with pytest.raises(ValueError, match="security_id"):
        DailyBarSeries(SECURITY, [bar(security_id=OTHER)])
    with pytest.raises(ValueError, match="unsupported"):
        bar(schema_version="daily-bar-v2")


def test_trading_day_type_prevents_datetime_or_timezone_ambiguity() -> None:
    with pytest.raises(TypeError, match="TradingDay"):
        bar(trading_day=date(2024, 1, 2))
