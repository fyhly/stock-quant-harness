"""Offline exact reproduction of immutable research runs."""

from dataclasses import dataclass
import hashlib
from typing import Callable, Mapping

from stock_quant.backtest import BacktestResult
from stock_quant.research.artifacts import RunStore
from stock_quant.research.manifest import (
    ExperimentManifest,
    IDENTITY_FIELDS,
    verify_manifest,
)
from stock_quant.research.run_id import RunId


class ReproductionError(RuntimeError):
    pass


ManifestLoader = Callable[[RunId], ExperimentManifest]
ConfigLoader = Callable[[RunId], bytes]
PipelineCallback = Callable[[ExperimentManifest, bytes], BacktestResult]


@dataclass(frozen=True)
class ReproductionResult:
    run_id: RunId
    fingerprint: str
    exact: bool


def reproduce_run(
    run_id: RunId,
    *,
    store: RunStore,
    manifest_loader: ManifestLoader,
    config_loader: ConfigLoader,
    current_identities: Mapping[str, str],
    pipeline: PipelineCallback,
) -> ReproductionResult:
    """Load and verify every pinned input before invoking an offline pipeline."""
    try:
        manifest = manifest_loader(run_id)
        verify_manifest(manifest)
        artifacts = store.load(run_id)
    except Exception as exc:
        raise ReproductionError("pinned run is missing, invalid, or tampered") from exc
    if manifest.run_id != run_id or artifacts.run_id != run_id:
        raise ReproductionError("run identity mismatch")
    if set(current_identities) != set(IDENTITY_FIELDS):
        raise ReproductionError("all current identities are required")
    drift = tuple(
        name
        for name in IDENTITY_FIELDS
        if current_identities[name] != getattr(manifest, f"{name}_identity")
    )
    if drift:
        raise ReproductionError("identity drift: " + ",".join(drift))
    config = config_loader(run_id)
    if hashlib.sha256(config).hexdigest() != manifest.config_identity:
        raise ReproductionError("pinned config identity mismatch")
    try:
        replay = pipeline(manifest, config)
    except Exception as exc:
        raise ReproductionError(
            "pipeline replay failed; original artifacts retained"
        ) from exc
    if (
        replay.fingerprint != manifest.backtest_identity
        or replay.fingerprint != artifacts.backtest_fingerprint
    ):
        raise ReproductionError("replay fingerprint mismatch")
    return ReproductionResult(run_id, replay.fingerprint, True)
