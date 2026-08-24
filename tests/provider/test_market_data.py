import json
from pathlib import Path

import pytest

from stock_quant.data import RawArtifactStore
from stock_quant.provider import acquire_daily, FakeTransport, TerminalProviderError


FIELDS = ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"]


def response(items: object) -> bytes:
    return json.dumps(
        {"code": 0, "msg": "", "data": {"fields": FIELDS, "items": items}},
        separators=(",", ":"),
    ).encode()


def test_exact_raw_before_parse_and_official_unit_conversion(tmp_path: Path) -> None:
    content = response(
        [["600000.SH", "20240102", "10.1", "10.5", "9.9", "10.2", "12", "34.5"]]
    )
    ref, series = acquire_daily(
        FakeTransport({"daily": content}),
        RawArtifactStore(tmp_path),
        credential="runtime",
        ts_code="600000.SH",
        start_date="20240101",
        end_date="20240102",
    )
    assert RawArtifactStore(tmp_path).read(ref.artifact_id) == content
    assert series.bars[0].volume == 1200
    assert str(series.bars[0].amount) == "34500.0"


def test_schema_error_payload_and_duplicates_fail_after_raw(tmp_path: Path) -> None:
    drift = json.dumps(
        {
            "code": 0,
            "msg": "",
            "data": {"fields": ["ts_code"], "items": [["600000.SH"]]},
        }
    ).encode()
    with pytest.raises(TerminalProviderError, match="schema drift"):
        acquire_daily(
            FakeTransport({"daily": drift}),
            RawArtifactStore(tmp_path / "drift"),
            credential="x",
            ts_code="600000.SH",
            start_date="20240101",
            end_date="20240102",
        )
    duplicate = response(
        [["600000.SH", "20240102", "10", "10", "10", "10", "1", "1"]] * 2
    )
    with pytest.raises(TerminalProviderError, match="duplicate"):
        acquire_daily(
            FakeTransport({"daily": duplicate}),
            RawArtifactStore(tmp_path / "dupe"),
            credential="x",
            ts_code="600000.SH",
            start_date="20240101",
            end_date="20240102",
        )
    error = json.dumps(
        {"code": -1, "msg": "bad", "data": {"fields": FIELDS, "items": []}}
    ).encode()
    with pytest.raises(TerminalProviderError, match="error payload"):
        acquire_daily(
            FakeTransport({"daily": error}),
            RawArtifactStore(tmp_path / "error"),
            credential="x",
            ts_code="600000.SH",
            start_date="20240101",
            end_date="20240102",
        )
