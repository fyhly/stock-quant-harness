from datetime import date

import pytest

from stock_quant.daily.quality import DailyQualityEvidence, DailyQualityFailure
from stock_quant.daily.universe_refresh import refresh_daily_universe
from stock_quant.domain import SecurityId
from stock_quant.universe.engine import SecurityExclusions, UniverseResult
from stock_quant.universe.rules import Exclusion, ExclusionCode
from stock_quant.universe.snapshot import UniverseSnapshot


DAY = date(2020, 1, 2)
A, B = SecurityId.parse("000001.XSHE"), SecurityId.parse("600000.XSHG")
PASS = DailyQualityEvidence(True, (), (), ("bars",))


def build(as_of: date) -> UniverseResult:
    assert as_of == DAY
    exclusion = Exclusion(
        ExclusionCode.MISSING_INDEX_HISTORY, "pit", "missing fact", ()
    )
    return UniverseResult(as_of, "v1", (A,), (SecurityExclusions(B, (exclusion,)),))


def test_historical_date_is_passed_to_pit_builder_and_exclusions_are_deterministic() -> (
    None
):
    def refresh() -> UniverseSnapshot:
        return refresh_daily_universe(
            PASS,
            as_of=DAY,
            build_pit=build,
            local_data_identities=("a" * 64,),
            code_identity="b" * 64,
            config_identity="c" * 64,
        )

    first = refresh()
    assert first == refresh() and first.as_of == DAY
    assert (
        first.included == (A,)
        and first.excluded[0].reasons[0].message == "missing fact"
    )


def test_quality_failure_prevents_builder_and_date_mismatch_fails() -> None:
    calls = []

    def should_not_build(day: date) -> UniverseResult:
        calls.append(day)
        return build(day)

    with pytest.raises(DailyQualityFailure):
        refresh_daily_universe(
            DailyQualityEvidence(False, ("fatal",), (), ()),
            as_of=DAY,
            build_pit=should_not_build,
            local_data_identities=("a" * 64,),
            code_identity="b" * 64,
            config_identity="c" * 64,
        )
    assert calls == []
    with pytest.raises(ValueError, match="date mismatch"):
        refresh_daily_universe(
            PASS,
            as_of=DAY,
            build_pit=lambda _: UniverseResult(date(2020, 1, 3), "v1", (), ()),
            local_data_identities=("a" * 64,),
            code_identity="b" * 64,
            config_identity="c" * 64,
        )
