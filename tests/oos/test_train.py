from datetime import date

from stock_quant.oos.train import BoundedAccessError, run_train
from stock_quant.oos.windows import OOSWindowSet, TimeWindow


WINDOWS = OOSWindowSet.create(
    TimeWindow(date(2024, 1, 1), date(2024, 1, 3)),
    TimeWindow(date(2024, 1, 3), date(2024, 1, 4)),
    TimeWindow(date(2024, 1, 4), date(2024, 1, 5)),
)


def test_train_is_bounded_and_repeatable() -> None:
    data = {date(2024, 1, day): str(day) for day in range(1, 5)}

    def fit(context):  # type: ignore[no-untyped-def]
        return context.get(date(2024, 1, 1)).encode(), b"fixed"

    first = run_train(WINDOWS, data, fit)
    assert first == run_train(WINDOWS, data, fit) and first.succeeded
    assert first.fitted is not None and len(first.fitted.artifact_identity) == 64


def test_outside_access_failure_is_retained() -> None:
    def leak(context):  # type: ignore[no-untyped-def]
        context.get(date(2024, 1, 3))
        return b"", b""

    result = run_train(WINDOWS, {}, leak)
    assert not result.succeeded and result.failure_type == BoundedAccessError.__name__
    assert "outside" in result.failure_message
