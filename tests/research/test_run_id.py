from datetime import datetime, timezone
from pathlib import Path
import pytest
from stock_quant.research import RunId, RunRegistry, RunRegistryError


def test_unique_canonical_ids_and_lookup(tmp_path: Path) -> None:
    first, second = RunId.generate(), RunId.generate()
    assert first != second
    registry = RunRegistry(tmp_path)
    record = registry.register(first, datetime(2024, 1, 1, tzinfo=timezone.utc))
    assert registry.lookup(first) == record and record.status == "CREATED"


def test_invalid_and_no_overwrite_collision(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="canonical"):
        RunId("../bad")
    registry, run_id = RunRegistry(tmp_path), RunId.generate()
    registry.register(run_id, datetime.now(timezone.utc))
    with pytest.raises(RunRegistryError, match="already"):
        registry.register(run_id, datetime.now(timezone.utc))
