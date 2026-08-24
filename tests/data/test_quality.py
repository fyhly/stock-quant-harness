from datetime import date, time
from decimal import Decimal

from stock_quant.data import (
    assess_daily_bars,
    DailyBar,
    QualityIssueCode,
    QualityReport,
    QualitySeverity,
)
from stock_quant.domain import (
    Exchange,
    SecurityId,
    TradingCalendar,
    TradingDay,
    TradingSession,
)


SECURITY = SecurityId("600000", Exchange.SHANGHAI)


def bar(day: int, close: str = "10") -> DailyBar:
    close_value = Decimal(close)
    return DailyBar(
        SECURITY,
        TradingDay(date(2024, 1, day)),
        open=Decimal("10"),
        high=max(Decimal("10"), close_value),
        low=min(Decimal("10"), close_value),
        close=close_value,
        volume=100,
        amount=Decimal("1000"),
    )


def issue_codes(report: QualityReport) -> list[QualityIssueCode]:
    return [issue.code for issue in report.issues]


def test_clean_report_is_empty_pass_and_deterministic() -> None:
    first = assess_daily_bars([bar(2), bar(3)])
    second = assess_daily_bars([bar(2), bar(3)])

    assert first.issues == ()
    assert first.passed
    assert first.report_id == second.report_id


def test_empty_input_is_explicit_warning() -> None:
    report = assess_daily_bars([])

    assert report.issues[0].code is QualityIssueCode.EMPTY_INPUT
    assert report.issues[0].severity is QualitySeverity.WARNING
    assert report.passed


def test_duplicates_and_order_are_reported_without_repair() -> None:
    observations = [bar(3), bar(2), bar(2)]
    report = assess_daily_bars(observations)

    assert QualityIssueCode.OUT_OF_ORDER in issue_codes(report)
    assert QualityIssueCode.DUPLICATE_DATE in issue_codes(report)
    assert [item.trading_day.value.day for item in observations] == [3, 2, 2]
    assert not report.passed


def test_missing_date_uses_only_injected_calendar() -> None:
    session = TradingSession("day", time(9, 30), time(15))
    calendar = TradingCalendar(
        {
            TradingDay(date(2024, 1, 2)): (session,),
            TradingDay(date(2024, 1, 3)): (session,),
            TradingDay(date(2024, 1, 4)): (session,),
        },
        coverage_start=date(2024, 1, 1),
        coverage_end=date(2024, 1, 7),
        timezone="Asia/Shanghai",
    )

    report = assess_daily_bars([bar(2), bar(4)], calendar=calendar)

    missing = [
        issue
        for issue in report.issues
        if issue.code is QualityIssueCode.MISSING_TRADING_DAY
    ]
    assert [issue.trading_date for issue in missing] == [date(2024, 1, 3)]


def test_defensive_ohlc_and_volume_checks_detect_corruption() -> None:
    corrupted = bar(2)
    object.__setattr__(corrupted, "high", Decimal("1"))
    object.__setattr__(corrupted, "volume", -1)

    report = assess_daily_bars([corrupted])

    assert QualityIssueCode.OHLC_INVARIANT in issue_codes(report)
    assert QualityIssueCode.NEGATIVE_VOLUME_OR_AMOUNT in issue_codes(report)
    assert not report.passed


def test_extreme_return_is_warning_with_evidence() -> None:
    report = assess_daily_bars(
        [bar(2, "10"), bar(3, "20")],
        extreme_return_threshold=Decimal("0.50"),
    )

    issue = report.issues[0]
    assert issue.code is QualityIssueCode.EXTREME_CLOSE_RETURN
    assert issue.severity is QualitySeverity.WARNING
    assert issue.evidence == (("absolute_return", "1"), ("threshold", "0.50"))
