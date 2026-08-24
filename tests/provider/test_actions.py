import json
from pathlib import Path

import pytest

from stock_quant.data import RawArtifactStore
from stock_quant.provider import (
    acquire_corporate_actions,
    FakeTransport,
    TerminalProviderError,
)
from stock_quant.provider.actions import DIVIDEND_FIELDS, RIGHTS_FIELDS


def payload(fields: object, items: object) -> bytes:
    return json.dumps(
        {"code": 0, "msg": "", "data": {"fields": fields, "items": items}}
    ).encode()


def test_actions_preserve_dates_types_and_raw_lineage(tmp_path: Path) -> None:
    dividend = payload(
        DIVIDEND_FIELDS,
        [
            [
                "20240101",
                "1",
                "20240103",
                "20240104",
                "20240102",
                "0.1",
                "0.2",
                "600000.SH",
            ]
        ],
    )
    rights = payload(
        RIGHTS_FIELDS,
        [["20240101", "20240103", "20240104", "20240102", "5", "0.3", "600000.SH"]],
    )
    batch = acquire_corporate_actions(
        FakeTransport({"dividend": dividend, "rights_issue": rights}),
        RawArtifactStore(tmp_path),
        credential="x",
        ts_code="600000.SH",
    )
    assert len(batch.actions) == 3
    assert {action.source_identity for action in batch.actions} == {
        ref.artifact_id for ref in batch.raw_refs
    }


def test_missing_dates_fail_after_raw_trace(tmp_path: Path) -> None:
    bad = payload(
        DIVIDEND_FIELDS,
        [["", "1", "20240103", "20240104", "20240102", "0", "0", "600000.SH"]],
    )
    with pytest.raises(TerminalProviderError, match="dates"):
        acquire_corporate_actions(
            FakeTransport(
                {"dividend": bad, "rights_issue": payload(RIGHTS_FIELDS, [])}
            ),
            RawArtifactStore(tmp_path),
            credential="x",
            ts_code="600000.SH",
        )
    assert tuple(tmp_path.rglob("payload.bin"))
