from dataclasses import replace
from datetime import date
import hashlib

import pytest

from stock_quant.daily.replay import (
    DailyReplayError,
    DailyReplaySpec,
    replay_daily_report,
)
from stock_quant.daily.report import DailyResearchReport


DAY = date(2024, 1, 2)
RAW = b"immutable local daily inputs"
REPORT = DailyResearchReport(
    "<html>offline exact</html>",
    hashlib.sha256(b"<html>offline exact</html>").hexdigest(),
    "QUALITY_FAILED_NO_SIGNAL",
)
SPEC = DailyReplaySpec(
    DAY,
    (DAY,),
    (("git", "a" * 64),),
    (("daily.json", hashlib.sha256(RAW).hexdigest()),),
    REPORT.fingerprint,
)


def test_exact_repeat_uses_only_injected_local_bytes() -> None:
    calls = []

    def load(name: str) -> bytes:
        calls.append(name)
        return RAW

    def reconstruct(inputs):  # type: ignore[no-untyped-def]
        assert inputs == {"daily.json": RAW}
        return REPORT

    first = replay_daily_report(
        SPEC,
        current_identities={"git": "a" * 64},
        load_local=load,
        reconstruct=reconstruct,
    )
    second = replay_daily_report(
        SPEC,
        current_identities={"git": "a" * 64},
        load_local=load,
        reconstruct=reconstruct,
    )
    assert first == second and first.exact and calls == ["daily.json", "daily.json"]


def test_tamper_missing_drift_coverage_and_fingerprint_fail_closed() -> None:
    with pytest.raises(DailyReplayError, match="tamper"):
        replay_daily_report(
            SPEC,
            current_identities={"git": "a" * 64},
            load_local=lambda _: b"changed",
            reconstruct=lambda _: REPORT,
        )
    with pytest.raises(DailyReplayError, match="missing"):
        replay_daily_report(
            SPEC,
            current_identities={"git": "a" * 64},
            load_local=lambda _: (_ for _ in ()).throw(FileNotFoundError()),
            reconstruct=lambda _: REPORT,
        )
    with pytest.raises(DailyReplayError, match="drift"):
        replay_daily_report(
            SPEC,
            current_identities={"git": "b" * 64},
            load_local=lambda _: RAW,
            reconstruct=lambda _: REPORT,
        )
    with pytest.raises(DailyReplayError, match="coverage"):
        replay_daily_report(
            replace(SPEC, report_date=date(2024, 1, 3)),
            current_identities={"git": "a" * 64},
            load_local=lambda _: RAW,
            reconstruct=lambda _: REPORT,
        )
    with pytest.raises(DailyReplayError, match="fingerprint"):
        replay_daily_report(
            replace(SPEC, expected_fingerprint="f" * 64),
            current_identities={"git": "a" * 64},
            load_local=lambda _: RAW,
            reconstruct=lambda _: REPORT,
        )
