from pathlib import Path
import pytest
from stock_quant.backtest import BacktestResult, create_backtest_result
from stock_quant.research.artifacts import RunArtifactError, RunStore
from stock_quant.research import RunId


def result() -> BacktestResult:
    return create_backtest_result(
        fills=(),
        rejections=(),
        holdings=(),
        equity=(),
        trade_ledger=(),
        action_ledger_keys=(),
        config_identity="a" * 64,
        data_identity="b" * 64,
        code_identity="c" * 64,
    )


def test_round_trip_no_overwrite_and_backtest_adapter(tmp_path: Path) -> None:
    store, run_id = RunStore(tmp_path), RunId.generate()
    first = store.publish(
        run_id, result(), metrics={"return": "0"}, failures=("visible failure",)
    )
    assert store.load(run_id) == first and len(first.files) == 5
    with pytest.raises(RunArtifactError, match="already"):
        store.publish(run_id, result(), metrics={}, failures=())


def test_partial_cleanup_and_tamper_detection(tmp_path: Path) -> None:
    store, failed = RunStore(tmp_path), RunId.generate()
    with pytest.raises(RunArtifactError, match="injected"):
        store.publish(failed, result(), metrics={}, failures=(), fail_after_stage=True)
    assert not (tmp_path / failed.value).exists()
    good = RunId.generate()
    store.publish(good, result(), metrics={}, failures=())
    (tmp_path / good.value / "metrics.json").write_text("tamper")
    with pytest.raises(RunArtifactError, match="tamper"):
        store.load(good)
