from datetime import date
from decimal import Decimal

import pytest

from stock_quant.oos.stitch import (
    OOSReturnPoint,
    OOSReturnSegment,
    StitchError,
    stitch_oos_results,
)
from stock_quant.oos.windows import TimeWindow


def segment(
    start: int, end: int, values: tuple[tuple[int, str], ...], identity: str
) -> OOSReturnSegment:
    return OOSReturnSegment(
        identity,
        TimeWindow(date(2024, 1, start), date(2024, 1, end)),
        tuple(
            OOSReturnPoint(date(2024, 1, day), Decimal(value)) for day, value in values
        ),
    )


def test_compounding_boundary_provenance_and_reconciliation() -> None:
    segments = (
        segment(2, 4, ((2, ".1"), (3, "-.1")), "a" * 64),
        segment(4, 5, ((4, ".2"),), "b" * 64),
    )
    result = stitch_oos_results(
        segments,
        tuple(date(2024, 1, day) for day in (2, 3, 4)),
        initial_cash=Decimal(100),
    )
    assert tuple(point.equity for point in result.points) == (
        Decimal(110),
        Decimal(99),
        Decimal("118.8"),
    )
    assert result.final_equity == Decimal("118.8")
    assert tuple(point.window_identity for point in result.points) == (
        "a" * 64,
        "a" * 64,
        "b" * 64,
    )


def test_duplicate_gap_and_order_fail_closed() -> None:
    first = segment(2, 4, ((2, ".1"),), "a" * 64)
    with pytest.raises(StitchError, match="gap"):
        stitch_oos_results(
            (first,), (date(2024, 1, 2), date(2024, 1, 3)), initial_cash=Decimal(1)
        )
    duplicate = segment(2, 4, ((2, ".1"),), "b" * 64)
    with pytest.raises(StitchError, match="duplicate|overlap"):
        stitch_oos_results(
            (first, duplicate), (date(2024, 1, 2),), initial_cash=Decimal(1)
        )
    later = segment(4, 5, ((4, ".1"),), "c" * 64)
    with pytest.raises(StitchError, match="ordered"):
        stitch_oos_results(
            (later, first),
            (date(2024, 1, 4), date(2024, 1, 2)),
            initial_cash=Decimal(1),
        )
