import hashlib
from pathlib import Path

import pytest

from stock_quant.backtest import BacktestResult, create_backtest_result
from stock_quant.research.artifacts import RunStore
from stock_quant.research.manifest import (
    ExperimentManifest,
    IDENTITY_FIELDS,
    create_manifest,
)
from stock_quant.research.reproduce import ReproductionError, reproduce_run
from stock_quant.research.run_id import RunId


def backtest() -> BacktestResult:
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


def setup(
    tmp_path: Path,
) -> tuple[
    RunId,
    BacktestResult,
    bytes,
    dict[str, str],
    ExperimentManifest,
    RunStore,
]:
    run_id, replay = RunId.generate(), backtest()
    config = b"fixed offline config"
    identities = {
        name: hashlib.sha256(name.encode()).hexdigest() for name in IDENTITY_FIELDS
    }
    identities["config"] = hashlib.sha256(config).hexdigest()
    identities["backtest"] = replay.fingerprint
    manifest = create_manifest(run_id, identities)
    store = RunStore(tmp_path)
    store.publish(run_id, replay, metrics={}, failures=("original visible failure",))
    return run_id, replay, config, identities, manifest, store


def test_exact_offline_replay(tmp_path: Path) -> None:
    run_id, replay, config, identities, manifest, store = setup(tmp_path)
    calls = []

    def pipeline(pinned: ExperimentManifest, raw: bytes) -> BacktestResult:
        calls.append((pinned, raw))
        return replay

    result = reproduce_run(
        run_id,
        store=store,
        manifest_loader=lambda _: manifest,
        config_loader=lambda _: config,
        current_identities=identities,
        pipeline=pipeline,
    )
    assert result.exact and result.fingerprint == replay.fingerprint
    assert calls == [(manifest, config)]


def test_identity_config_fingerprint_and_tamper_fail_closed(tmp_path: Path) -> None:
    run_id, replay, config, identities, manifest, store = setup(tmp_path)

    def manifest_loader(_run_id: RunId) -> ExperimentManifest:
        return manifest

    def config_loader(_run_id: RunId) -> bytes:
        return config

    def pipeline(_manifest: ExperimentManifest, _config: bytes) -> BacktestResult:
        return replay

    drifted = dict(identities)
    drifted["schema"] = "f" * 64
    with pytest.raises(ReproductionError, match="identity drift"):
        reproduce_run(
            run_id,
            store=store,
            manifest_loader=manifest_loader,
            config_loader=config_loader,
            current_identities=drifted,
            pipeline=pipeline,
        )
    with pytest.raises(ReproductionError, match="config identity"):
        reproduce_run(
            run_id,
            store=store,
            manifest_loader=manifest_loader,
            config_loader=lambda _: b"wrong",
            current_identities=identities,
            pipeline=pipeline,
        )
    (tmp_path / run_id.value / "metrics.json").write_text("tamper")
    with pytest.raises(ReproductionError, match="tampered"):
        reproduce_run(
            run_id,
            store=store,
            manifest_loader=manifest_loader,
            config_loader=config_loader,
            current_identities=identities,
            pipeline=pipeline,
        )


def test_pipeline_failure_retains_original_failure_artifact(tmp_path: Path) -> None:
    run_id, _replay, config, identities, manifest, store = setup(tmp_path)
    failure_path = tmp_path / run_id.value / "failures.json"
    before = failure_path.read_bytes()

    def fail(_manifest: ExperimentManifest, _config: bytes) -> BacktestResult:
        raise RuntimeError("offline replay failure")

    with pytest.raises(ReproductionError, match="retained"):
        reproduce_run(
            run_id,
            store=store,
            manifest_loader=lambda _: manifest,
            config_loader=lambda _: config,
            current_identities=identities,
            pipeline=fail,
        )
    assert failure_path.read_bytes() == before
