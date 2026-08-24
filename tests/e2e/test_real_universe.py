from datetime import date
from pathlib import Path
from stock_quant.e2e import build_real_universe

ROOT = Path(__file__).parents[1] / "fixtures" / "real" / "v1"


def test_real_universe_pit_snapshot_is_reproducible() -> None:
    first = build_real_universe(ROOT, date(2024, 12, 16))
    second = build_real_universe(ROOT, date(2024, 12, 16))
    assert first == second and tuple(str(item) for item in first.included) == (
        "000001.XSHE",
        "600000.XSHG",
    )
    assert first.excluded == () and first.rule_version == "real-universe-v1"


def test_sample_master_retains_both_exchange_identities() -> None:
    result = build_real_universe(ROOT, date(2023, 7, 3))
    assert len(result.included) == 2
