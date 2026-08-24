from datetime import date

import pytest

from stock_quant.oos.windows import OOSWindowSet, TimeWindow, WindowValidationError


def window(start: int, end: int) -> TimeWindow:
    return TimeWindow(date(2024, 1, start), date(2024, 1, end))


def test_half_open_boundaries_adjacency_gap_and_identity() -> None:
    train = window(1, 5)
    assert train.contains(date(2024, 1, 1)) and not train.contains(date(2024, 1, 5))
    adjacent = OOSWindowSet.create(train, window(5, 7), window(7, 9))
    assert adjacent == OOSWindowSet.create(train, window(5, 7), window(7, 9))
    assert OOSWindowSet.create(train, window(6, 8), window(9, 10), embargo_days=1)


def test_reversal_overlap_and_embargo_violations_fail() -> None:
    with pytest.raises(WindowValidationError, match="nonempty"):
        window(5, 5)
    with pytest.raises(WindowValidationError, match="overlap"):
        OOSWindowSet.create(window(1, 5), window(4, 7), window(7, 9))
    with pytest.raises(WindowValidationError, match="embargo"):
        OOSWindowSet.create(window(1, 5), window(5, 7), window(7, 9), embargo_days=1)
