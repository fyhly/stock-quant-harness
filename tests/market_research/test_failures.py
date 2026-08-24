from datetime import date
from pathlib import Path

import pytest

from stock_quant.domain import SecurityId
from stock_quant.market_research.failures import (
    FailureRegistry,
    FailureRegistryError,
    render_market_summary,
)
from stock_quant.market_research.runner import (
    MarketBatchResult,
    MarketWorkItem,
    run_cross_sectional_batch,
)


def failed_batch() -> MarketBatchResult:
    items = (
        MarketWorkItem(date(2024, 1, 2), SecurityId.parse("000001.XSHE"), "a" * 64),
        MarketWorkItem(date(2024, 1, 2), SecurityId.parse("600000.XSHG"), "a" * 64),
    )

    def execute(item: MarketWorkItem) -> str:
        if item.security_id.code == "000001":
            raise ValueError("bad <sample>")
        return "ok"

    return run_cross_sectional_batch(items, execute, partition_size=1)


def test_append_only_idempotent_failure_and_offline_reconciled_report(
    tmp_path: Path,
) -> None:
    batch, registry = failed_batch(), FailureRegistry(tmp_path)
    record = next(item for item in batch.records if not item.succeeded)
    kwargs = dict(
        run_identity="b" * 64,
        data_identity="c" * 64,
        git_identity="d" * 64,
        config_identity="e" * 64,
    )
    first = registry.retain(record, **kwargs)
    assert registry.retain(record, **kwargs) == first
    assert registry.read(first.failure_id) == first
    report = render_market_summary(batch, (first,))
    assert "Total: 2; succeeded: 1; failed: 1" in report
    assert "bad &lt;sample&gt;" in report and "RESEARCH ONLY" in report
    assert "http://" not in report and "https://" not in report


def test_no_silent_failure_filtering_or_overwrite(tmp_path: Path) -> None:
    batch, registry = failed_batch(), FailureRegistry(tmp_path)
    record = next(item for item in batch.records if not item.succeeded)
    evidence = registry.retain(
        record,
        run_identity="b" * 64,
        data_identity="c" * 64,
        git_identity="d" * 64,
        config_identity="e" * 64,
    )
    with pytest.raises(FailureRegistryError, match="reconcile"):
        render_market_summary(batch, ())
    path = tmp_path / f"{evidence.failure_id}.json"
    path.write_text("tamper")
    with pytest.raises(FailureRegistryError, match="tamper"):
        registry.retain(
            record,
            run_identity="b" * 64,
            data_identity="c" * 64,
            git_identity="d" * 64,
            config_identity="e" * 64,
        )
