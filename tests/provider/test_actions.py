import json
from decimal import Decimal
from pathlib import Path
import pytest
from stock_quant.actions import BonusShareEvent
from stock_quant.data import RawArtifactStore
from stock_quant.provider import (
    acquire_corporate_actions,
    acquire_tushare_rights,
    CapabilityUnavailableError,
    FakeTransport,
    ProviderQuery,
    TerminalProviderError,
)
from stock_quant.provider.actions import DIVIDEND_FIELDS


def payload(items: object) -> bytes:
    return json.dumps(
        {"code": 0, "msg": "", "data": {"fields": DIVIDEND_FIELDS, "items": items}}
    ).encode()


def test_official_dividend_cash_bonus_transfer_mapping(tmp_path: Path) -> None:
    content = payload(
        [
            [
                "20240101",
                "1",
                "20240105",
                "20240103",
                "20240104",
                "20240102",
                "0.1",
                "0.2",
                "0.3",
                "600000.SH",
            ]
        ]
    )
    fake = FakeTransport({"dividend": content})
    batch = acquire_corporate_actions(
        fake, RawArtifactStore(tmp_path), credential="x", ts_code="600000.SH"
    )
    assert len(batch.actions) == 2 and tuple(
        query.endpoint for query in fake.queries
    ) == ("dividend",)
    bonus = next(
        action for action in batch.actions if isinstance(action, BonusShareEvent)
    )
    assert bonus.bonus_ratio == Decimal("0.1") and bonus.transfer_ratio == Decimal(
        "0.2"
    )
    assert bonus.share_credit_date.isoformat() == "2024-01-05"


def test_rights_unavailable_without_request_and_https_required() -> None:
    fake = FakeTransport({})
    with pytest.raises(CapabilityUnavailableError, match="not verified"):
        acquire_tushare_rights(fake, credential="x")
    assert fake.queries == []
    with pytest.raises(ValueError, match="HTTPS"):
        ProviderQuery("daily", (), (), "v1", base_url="http://api.tushare.pro")


def test_official_total_mismatch_fails_after_raw(tmp_path: Path) -> None:
    bad = payload(
        [
            [
                "20240101",
                "0",
                "20240105",
                "20240103",
                "20240104",
                "20240102",
                "0.1",
                "0.2",
                "9",
                "600000.SH",
            ]
        ]
    )
    with pytest.raises(TerminalProviderError, match="mapping"):
        acquire_corporate_actions(
            FakeTransport({"dividend": bad}),
            RawArtifactStore(tmp_path),
            credential="x",
            ts_code="600000.SH",
        )
    assert tuple(tmp_path.rglob("payload.bin"))
