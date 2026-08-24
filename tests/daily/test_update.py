from pathlib import Path
from typing import NoReturn

import pytest

from stock_quant.daily.update import DailyUpdateError, run_daily_update
from stock_quant.provider.sync import SyncManifest


def manifest(dataset: str) -> SyncManifest:
    return SyncManifest(
        dataset,
        "2024-01-02",
        "a" * 64,
        "b" * 64,
        ("c" if dataset == "bars" else "d") * 64,
    )


def test_repeat_is_idempotent_atomic_and_has_no_implicit_network(
    tmp_path: Path,
) -> None:
    calls = []

    def update_bars() -> SyncManifest:
        calls.append("bars")
        return manifest("bars")

    result = run_daily_update(
        tmp_path,
        run_identity="e" * 64,
        watermark="2024-01-02",
        dataset_updates=(("bars", update_bars),),
    )
    repeat = run_daily_update(
        tmp_path,
        run_identity="e" * 64,
        watermark="2024-01-02",
        dataset_updates=(
            ("bars", lambda: (_ for _ in ()).throw(AssertionError("network"))),
        ),
    )
    assert (
        result == repeat and calls == ["bars"] and result.recovery_state == "PUBLISHED"
    )


def test_partial_schema_network_failure_does_not_publish_or_overwrite(
    tmp_path: Path,
) -> None:
    def fail() -> NoReturn:
        raise RuntimeError("network/schema")

    with pytest.raises(DailyUpdateError, match="after 1"):
        run_daily_update(
            tmp_path,
            run_identity="f" * 64,
            watermark="2024-01-02",
            dataset_updates=(("bars", lambda: manifest("bars")), ("financial", fail)),
        )
    assert not (tmp_path / f"{'f' * 64}.json").exists()
    good = run_daily_update(
        tmp_path,
        run_identity="g" * 64,
        watermark="2024-01-02",
        dataset_updates=(("bars", lambda: manifest("bars")),),
    )
    (tmp_path / f"{'g' * 64}.json").write_text("tamper")
    with pytest.raises(DailyUpdateError, match="corrupt|tamper"):
        run_daily_update(
            tmp_path,
            run_identity=good.run_identity,
            watermark="2024-01-02",
            dataset_updates=(("bars", lambda: manifest("bars")),),
        )
