import json
from pathlib import Path

import pytest

from stock_quant.data import RawArtifactStore
from stock_quant.provider import (
    acquire_effective_history,
    CapabilityUnavailableError,
    FakeTransport,
)


def payload(fields: object, items: object) -> bytes:
    return json.dumps(
        {"code": 0, "msg": "", "data": {"fields": fields, "items": items}}
    ).encode()


def test_entry_exit_effective_dates_and_gaps_are_retained(tmp_path: Path) -> None:
    fields = ["index_code", "ts_code", "effective_from", "effective_to"]
    content = payload(
        fields,
        [
            ["000300.SH", "600000.SH", "20200101", "20210101"],
            ["000300.SH", "600000.SH", "20220101", None],
        ],
    )
    ref, rows = acquire_effective_history(
        FakeTransport({"index_history": content}),
        RawArtifactStore(tmp_path),
        credential="x",
        endpoint="index_history",
        subject_field="index_code",
    )
    assert len(rows) == 2 and rows[0].effective_to is not None
    assert (
        rows[1].effective_from.year == 2022 and rows[0].raw_identity == ref.artifact_id
    )


def test_current_only_index_or_industry_response_is_unavailable(tmp_path: Path) -> None:
    current = payload(["ts_code", "industry_code"], [["600000.SH", "BANK"]])
    with pytest.raises(CapabilityUnavailableError, match="lacks"):
        acquire_effective_history(
            FakeTransport({"industry": current}),
            RawArtifactStore(tmp_path),
            credential="x",
            endpoint="industry",
            subject_field="industry_code",
        )
