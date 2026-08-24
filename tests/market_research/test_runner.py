from datetime import date

from stock_quant.domain import SecurityId
from stock_quant.market_research.runner import MarketWorkItem, run_cross_sectional_batch


def item(day: int, code: str) -> MarketWorkItem:
    exchange = "XSHE" if code.startswith("0") else "XSHG"
    return MarketWorkItem(
        date(2024, 1, day), SecurityId.parse(f"{code}.{exchange}"), "a" * 64
    )


def test_batch_order_partition_manifest_and_repeat_identity() -> None:
    items = (item(3, "600000"), item(2, "000001"), item(2, "600000"))
    first = run_cross_sectional_batch(
        items, lambda value: value.item_id, partition_size=2
    )
    second = run_cross_sectional_batch(
        reversed(items), lambda value: value.item_id, partition_size=2
    )
    assert first == second
    assert tuple(record.item for record in first.records) == tuple(sorted(items))
    assert first.total == first.succeeded == 3 and first.failed == 0


def test_partial_failures_are_retained_and_retry_identity_is_stable() -> None:
    bad, good = item(2, "000001"), item(2, "600000")

    def execute(value: MarketWorkItem) -> str:
        if value == bad:
            raise RuntimeError("bad sample")
        return "ok"

    result = run_cross_sectional_batch((good, bad), execute, partition_size=1)
    assert result.total == result.succeeded + result.failed == 2
    failure = next(record for record in result.records if not record.succeeded)
    assert failure.item_id == bad.item_id and failure.failure_type == "RuntimeError"
    retry = run_cross_sectional_batch((bad,), execute, partition_size=1)
    assert retry.records[0].item_id == failure.item_id
