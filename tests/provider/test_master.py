import json
from datetime import date
from pathlib import Path

import pytest

from stock_quant.data import RawArtifactStore
from stock_quant.domain import ListingStatus
from stock_quant.provider import (
    acquire_security_master,
    FakeTransport,
    TerminalProviderError,
)


FIELDS = ["ts_code", "name", "list_status", "list_date", "delist_date"]


def payload(items: object) -> bytes:
    return json.dumps(
        {"code": 0, "msg": "", "data": {"fields": FIELDS, "items": items}}
    ).encode()


def test_delisted_identity_and_lifecycle_are_retained(tmp_path: Path) -> None:
    content = payload(
        [
            ["600000.SH", "Alive", "L", "20000101", None],
            ["600001.SH", "Gone", "D", "20000101", "20200101"],
        ]
    )
    batch = acquire_security_master(
        FakeTransport({"stock_basic": content}),
        RawArtifactStore(tmp_path),
        credential="x",
    )
    assert len(batch.master.securities) == len(batch.lifecycles) == 2
    assert batch.lifecycles[1].status_as_of(date(2021, 1, 1)) is ListingStatus.DELISTED
    assert RawArtifactStore(tmp_path).read(batch.raw.artifact_id) == content


def test_schema_and_chronology_failures_are_explicit(tmp_path: Path) -> None:
    bad = payload([["600000.SH", "Bad", "D", "20200102", "20200101"]])
    with pytest.raises(TerminalProviderError, match="chronology"):
        acquire_security_master(
            FakeTransport({"stock_basic": bad}),
            RawArtifactStore(tmp_path),
            credential="x",
        )
