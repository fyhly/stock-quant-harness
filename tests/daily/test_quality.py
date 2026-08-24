from dataclasses import replace
from decimal import Decimal

import pytest

from stock_quant.daily.quality import (
    DailyQualityConfig,
    DailyQualityFailure,
    DailyQualitySample,
    evaluate_daily_quality,
    invoke_after_quality,
)


CONFIG = DailyQualityConfig(1, Decimal(".8"), Decimal(".95"))


def sample() -> DailyQualitySample:
    return DailyQualitySample("bars", 0, Decimal(1), True, True, 0, True, True)


def test_warning_passes_but_missing_stale_corrupt_and_anomalies_are_fatal() -> None:
    warning = evaluate_daily_quality(
        (replace(sample(), coverage=Decimal(".9")),), CONFIG
    )
    assert warning.passed and warning.warnings == ("bars:LOW_COVERAGE",)
    assert not evaluate_daily_quality((), CONFIG).passed
    bad = evaluate_daily_quality(
        (
            replace(
                sample(),
                age_days=2,
                hash_valid=False,
                schema_valid=False,
                duplicate_count=1,
                ohlc_valid=False,
                calendar_valid=False,
            ),
        ),
        CONFIG,
    )
    assert not bad.passed
    assert set(item.split(":")[1] for item in bad.fatal_reasons) == {
        "STALE",
        "HASH",
        "SCHEMA",
        "DUPLICATES",
        "OHLC",
        "CALENDAR",
    }


def test_fatal_quality_never_invokes_downstream() -> None:
    calls = []
    failed = evaluate_daily_quality(
        (replace(sample(), coverage=Decimal(".1")),), CONFIG
    )
    with pytest.raises(DailyQualityFailure, match="COVERAGE"):
        invoke_after_quality(failed, lambda: calls.append("downstream"))
    assert calls == []
    assert (
        invoke_after_quality(evaluate_daily_quality((sample(),), CONFIG), lambda: "ok")
        == "ok"
    )
