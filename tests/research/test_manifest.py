from dataclasses import replace
import pytest
from stock_quant.research.manifest import (
    create_manifest,
    ManifestIntegrityError,
    verify_manifest,
)
from stock_quant.research import RunId

NAMES = (
    "git",
    "data",
    "config",
    "universe",
    "features",
    "strategy",
    "portfolio",
    "risk",
    "backtest",
    "schema",
)


def test_required_identity_hash_and_determinism() -> None:
    identities = {name: str(index % 10) * 64 for index, name in enumerate(NAMES)}
    run_id = RunId.generate()
    first = create_manifest(run_id, identities)
    assert first == create_manifest(run_id, identities) and first.research_only
    verify_manifest(first)


def test_invalid_tampered_and_nonresearch_manifest_fail() -> None:
    manifest = create_manifest(RunId.generate(), {name: "a" * 64 for name in NAMES})
    with pytest.raises(ManifestIntegrityError, match="mismatch"):
        verify_manifest(replace(manifest, data_identity="b" * 64))
    with pytest.raises(ManifestIntegrityError, match="research-only"):
        verify_manifest(replace(manifest, research_only=False))
