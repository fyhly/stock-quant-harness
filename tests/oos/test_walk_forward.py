from datetime import date
from decimal import Decimal

from stock_quant.oos.validation import ParameterCandidate
from stock_quant.oos.walk_forward import run_walk_forward
from stock_quant.oos.windows import OOSWindowSet, TimeWindow


def windows(offset: int) -> OOSWindowSet:
    return OOSWindowSet.create(
        TimeWindow(date(2024, 1, offset), date(2024, 1, offset + 2)),
        TimeWindow(date(2024, 1, offset + 2), date(2024, 1, offset + 3)),
        TimeWindow(date(2024, 1, offset + 3), date(2024, 1, offset + 4)),
    )


def test_multiple_windows_are_isolated_ordered_and_repeat_exactly() -> None:
    sets = (windows(1), windows(5))
    data = {date(2024, 1, day): day for day in range(1, 9)}

    def fit(context):  # type: ignore[no-untyped-def]
        try:
            value = context.get(date(2024, 1, 1))
        except Exception:
            value = context.get(date(2024, 1, 5))
        return str(value).encode(), b"base"

    def validate(_context, candidate):  # type: ignore[no-untyped-def]
        return Decimal(candidate.config.decode())

    def execute(context, _config):  # type: ignore[no-untyped-def]
        try:
            value = context.get(date(2024, 1, 4))
        except Exception:
            value = context.get(date(2024, 1, 8))
        return str(value).encode()

    args = (sets, data, (ParameterCandidate("one", b"1"),), fit, validate, execute)
    first = run_walk_forward(*args)
    assert first == run_walk_forward(*args) and first.total == first.succeeded == 2
    assert first.records[0].train.fitted != first.records[1].train.fitted


def test_failed_window_is_retained_and_totals_reconcile() -> None:
    sets = (windows(1), windows(5))

    def fit(context):  # type: ignore[no-untyped-def]
        return str(context.get(date(2024, 1, 1))).encode(), b"base"

    result = run_walk_forward(
        sets,
        {date(2024, 1, 1): 1},
        (ParameterCandidate("one", b"1"),),
        fit,
        lambda _c, _p: Decimal(1),
        lambda _c, _p: b"ok",
    )
    assert result.total == result.succeeded + result.failed == 2
    assert result.failed == 1 and result.records[1].failure_stage == "TRAIN"
