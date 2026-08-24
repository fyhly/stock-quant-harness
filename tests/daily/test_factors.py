from datetime import date, datetime, timezone
from decimal import Decimal

from stock_quant.daily.factors import DailyFactorRow, refresh_daily_factors
from stock_quant.daily.quality import DailyQualityEvidence
from stock_quant.domain import SecurityId
from stock_quant.universe.snapshot import UniverseSnapshot


DAY = date(2024, 1, 2)
CUTOFF = datetime(2024, 1, 2, 7, tzinfo=timezone.utc)
A, B = SecurityId.parse("000001.XSHE"), SecurityId.parse("600000.XSHG")
UNIVERSE = UniverseSnapshot(
    "a" * 64, DAY, (A, B), (), "v1", ("b" * 64,), "c" * 64, "d" * 64
)
PASS = DailyQualityEvidence(True, (), (), ("financial",))


def test_cutoff_pit_availability_lineage_failures_and_determinism() -> None:
    def compute(security: SecurityId, cutoff: datetime) -> DailyFactorRow:
        assert cutoff == CUTOFF
        if security == B:
            raise RuntimeError("missing announcement history")
        return DailyFactorRow(
            security,
            datetime(2024, 1, 2, 6, tzinfo=timezone.utc),
            (("value", Decimal(1)),),
        )

    first = refresh_daily_factors(
        PASS,
        UNIVERSE,
        decision_cutoff=CUTOFF,
        config_identity="e" * 64,
        lineage=("f" * 64,),
        compute=compute,
    )
    second = refresh_daily_factors(
        PASS,
        UNIVERSE,
        decision_cutoff=CUTOFF,
        config_identity="e" * 64,
        lineage=("f" * 64,),
        compute=compute,
    )
    assert first == second and first.rows[0].security_id == A
    assert (
        first.failures[0].security_id == B
        and "announcement" in first.failures[0].failure_message
    )


def test_future_announcement_and_wrong_security_become_visible_failures() -> None:
    def future(security: SecurityId, _cutoff: datetime) -> DailyFactorRow:
        return DailyFactorRow(
            B if security == A else security,
            datetime(2024, 1, 2, 8, tzinfo=timezone.utc),
            (("value", Decimal(1)),),
        )

    result = refresh_daily_factors(
        PASS,
        UNIVERSE,
        decision_cutoff=CUTOFF,
        config_identity="e" * 64,
        lineage=("f" * 64,),
        compute=future,
    )
    assert not result.rows and len(result.failures) == len(UNIVERSE.included)
    assert all("cutoff/alignment" in item.failure_message for item in result.failures)
