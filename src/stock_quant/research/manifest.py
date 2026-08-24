"""Canonical immutable experiment identity manifest."""

from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Dict
from stock_quant.research.run_id import RunId

_SHA = re.compile(r"^[0-9a-f]{64}$")
IDENTITY_FIELDS = (
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


class ManifestIntegrityError(ValueError):
    pass


@dataclass(frozen=True)
class ExperimentManifest:
    run_id: RunId
    git_identity: str
    data_identity: str
    config_identity: str
    universe_identity: str
    features_identity: str
    strategy_identity: str
    portfolio_identity: str
    risk_identity: str
    backtest_identity: str
    schema_identity: str
    research_only: bool
    manifest_identity: str


def create_manifest(run_id: RunId, identities: Dict[str, str]) -> ExperimentManifest:
    if set(identities) != set(IDENTITY_FIELDS) or any(
        not _SHA.fullmatch(value) for value in identities.values()
    ):
        raise ManifestIntegrityError(
            "all required identities must be lowercase SHA-256"
        )
    manifest = ExperimentManifest(
        run_id,
        identities["git"],
        identities["data"],
        identities["config"],
        identities["universe"],
        identities["features"],
        identities["strategy"],
        identities["portfolio"],
        identities["risk"],
        identities["backtest"],
        identities["schema"],
        True,
        "",
    )
    return replace(
        manifest, manifest_identity=hashlib.sha256(_canonical(manifest)).hexdigest()
    )


def verify_manifest(manifest: ExperimentManifest) -> None:
    if not manifest.research_only:
        raise ManifestIntegrityError("formal runs must be research-only")
    if hashlib.sha256(_canonical(manifest)).hexdigest() != manifest.manifest_identity:
        raise ManifestIntegrityError("manifest identity mismatch")


def _canonical(manifest: ExperimentManifest) -> bytes:
    payload = {"run_id": manifest.run_id.value, "research_only": manifest.research_only}
    payload.update(
        {name: getattr(manifest, f"{name}_identity") for name in IDENTITY_FIELDS}
    )
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
