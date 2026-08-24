from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from stock_quant.data import (
    ArtifactIntegrityError,
    InvalidArtifactError,
    RawArtifactMetadata,
    RawArtifactStore,
)


def metadata(**overrides: object) -> RawArtifactMetadata:
    values = {
        "source": "fixture.exchange",
        "query": {"symbols": ["600000.XSHG"], "start": "2024-01-01"},
        "fetched_at": datetime(2024, 2, 1, 8, tzinfo=timezone.utc),
        "schema_name": "daily-bars-raw",
        "schema_version": "v1",
    }
    values.update(overrides)
    return RawArtifactMetadata(**values)  # type: ignore[arg-type]


def artifact_path(root: Path, artifact_id: str) -> Path:
    return root / "sha256" / artifact_id[:2] / artifact_id


def test_stable_identity_and_idempotent_same_content(tmp_path: Path) -> None:
    store = RawArtifactStore(tmp_path)
    first = store.put(b"immutable bytes", metadata())
    second = store.put(b"immutable bytes", metadata())

    assert first == second
    assert store.read(first.artifact_id) == b"immutable bytes"
    assert first.content_hash == (
        "59d8792018a51a408d2738f31eedebd6fe9926cc4260fa168a38710bc51d7e30"
    )


def test_provenance_is_part_of_identity(tmp_path: Path) -> None:
    store = RawArtifactStore(tmp_path)
    first = store.put(b"same", metadata(source="source-one"))
    second = store.put(b"same", metadata(source="source-two"))

    assert first.artifact_id != second.artifact_id
    manifest = json.loads(
        (artifact_path(tmp_path, first.artifact_id) / "manifest.json").read_text()
    )
    assert manifest["metadata"]["source"] == "source-one"
    assert manifest["metadata"]["query"]["start"] == "2024-01-01"


def test_payload_tamper_is_detected_and_never_overwritten(tmp_path: Path) -> None:
    store = RawArtifactStore(tmp_path)
    ref = store.put(b"original", metadata())
    payload = artifact_path(tmp_path, ref.artifact_id) / "payload.bin"
    payload.write_bytes(b"tampered")

    with pytest.raises(ArtifactIntegrityError, match="payload"):
        store.read(ref.artifact_id)
    with pytest.raises(ArtifactIntegrityError, match="payload"):
        store.put(b"original", metadata())
    assert payload.read_bytes() == b"tampered"


def test_manifest_tamper_or_collision_is_detected(tmp_path: Path) -> None:
    store = RawArtifactStore(tmp_path)
    ref = store.put(b"original", metadata())
    manifest_path = artifact_path(tmp_path, ref.artifact_id) / "manifest.json"
    manifest_path.write_text("{}")

    with pytest.raises(ArtifactIntegrityError, match="manifest"):
        store.read(ref.artifact_id)
    with pytest.raises(ArtifactIntegrityError, match="manifest"):
        store.put(b"original", metadata())


@pytest.mark.parametrize("bad_name", ["../escape", "/absolute", "", "a/b"])
def test_path_like_metadata_is_rejected(bad_name: str) -> None:
    with pytest.raises(InvalidArtifactError):
        metadata(source=bad_name)


def test_invalid_metadata_and_traversal_reference_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(InvalidArtifactError, match="timezone-aware"):
        metadata(fetched_at=datetime(2024, 1, 1))
    with pytest.raises(InvalidArtifactError, match="floating-point"):
        metadata(query={"unstable": 1.2})
    with pytest.raises(InvalidArtifactError, match="SHA-256"):
        RawArtifactStore(tmp_path).read("../../etc/passwd")


def test_metadata_query_is_recursively_immutable() -> None:
    value = metadata(query={"symbols": ["600000.XSHG"]})

    with pytest.raises(TypeError):
        value.query["new"] = "mutation"  # type: ignore[index]
    symbols = value.query["symbols"]
    assert isinstance(symbols, tuple)
    with pytest.raises(TypeError):
        symbols[0] = "000001.XSHE"  # type: ignore[index]
