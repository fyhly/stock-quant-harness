from datetime import date
from decimal import Decimal

from stock_quant.domain import SecurityId
from stock_quant.market_research.universe_gate import evaluate_market_universe
from stock_quant.universe.snapshot import UniverseSnapshot


A = SecurityId.parse("000001.XSHE")
B = SecurityId.parse("600000.XSHG")


def snapshot() -> UniverseSnapshot:
    return UniverseSnapshot(
        "a" * 64, date(2024, 1, 2), (A, B), (), "v1", ("b" * 64,), "c" * 64, "d" * 64
    )


def test_coverage_boundary_passes_deterministically() -> None:
    first = evaluate_market_universe(
        snapshot(),
        {B: True, A: True},
        minimum_securities=2,
        minimum_coverage=Decimal(1),
    )
    second = evaluate_market_universe(
        snapshot(),
        {A: True, B: True},
        minimum_securities=2,
        minimum_coverage=Decimal(1),
    )
    assert first == second and first.passed and first.coverage == 1


def test_missing_bad_and_threshold_reasons_are_all_retained() -> None:
    evidence = evaluate_market_universe(
        snapshot(), {A: False}, minimum_securities=3, minimum_coverage=Decimal("0.5")
    )
    assert not evidence.passed
    assert evidence.reasons == (
        ("*", "MINIMUM_COVERAGE"),
        ("*", "MINIMUM_SECURITY_COUNT"),
        ("000001.XSHE", "BAD_QUALITY"),
        ("600000.XSHG", "MISSING_SAMPLE"),
    )
