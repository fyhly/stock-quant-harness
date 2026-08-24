import json
from pathlib import Path

import pytest

from stock_quant.data import RawArtifactStore
from stock_quant.provider import (
    acquire_financials,
    FakeTransport,
    TerminalProviderError,
)
from stock_quant.provider.financial import FIELDS


def payload(items: object) -> bytes:
    return json.dumps(
        {"code": 0, "msg": "", "data": {"fields": FIELDS, "items": items}}
    ).encode()


def test_announcement_report_period_and_revisions_are_retained(tmp_path: Path) -> None:
    content = payload(
        [
            ["20240301", "20231231", "10", "100", "600000.SH", "0"],
            ["20240401", "20231231", "11", "100", "600000.SH", "1"],
        ]
    )
    ref, rows = acquire_financials(
        FakeTransport({"income": content}),
        RawArtifactStore(tmp_path),
        credential="x",
        ts_code="600000.SH",
    )
    assert len(rows) == 2 and rows[0].report_period == rows[1].report_period
    assert rows[0].announcement_date < rows[1].announcement_date
    assert all(row.raw_identity == ref.artifact_id for row in rows)


def test_report_period_only_without_announcement_is_rejected(tmp_path: Path) -> None:
    content = payload([[None, "20231231", "10", "100", "600000.SH", "0"]])
    with pytest.raises(TerminalProviderError, match="announcement"):
        acquire_financials(
            FakeTransport({"income": content}),
            RawArtifactStore(tmp_path),
            credential="x",
            ts_code="600000.SH",
        )
