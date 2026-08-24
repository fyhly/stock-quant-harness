"""Raw-first ingestion of Tushare's documented dividend capability."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Tuple
from stock_quant.actions import BonusShareEvent, CashDividend
from stock_quant.actions.model import CorporateActionType
from stock_quant.data import RawArtifactMetadata, RawArtifactRef, RawArtifactStore
from stock_quant.domain import SecurityId
from stock_quant.provider.api import (
    ProviderQuery,
    ProviderTransport,
    TerminalProviderError,
)
from stock_quant.provider.history import CapabilityUnavailableError
from stock_quant.provider.tushare import _canonical_code, parse_rows

DIVIDEND_FIELDS = (
    "ann_date",
    "cash_div_tax",
    "div_listdate",
    "ex_date",
    "pay_date",
    "record_date",
    "stk_bo_rate",
    "stk_co_rate",
    "stk_div",
    "ts_code",
)


@dataclass(frozen=True)
class CorporateActionBatch:
    raw_refs: Tuple[RawArtifactRef, ...]
    actions: Tuple[CorporateActionType, ...]


def acquire_corporate_actions(
    transport: ProviderTransport,
    store: RawArtifactStore,
    *,
    credential: str,
    ts_code: str,
) -> CorporateActionBatch:
    query = ProviderQuery(
        "dividend", DIVIDEND_FIELDS, (("ts_code", ts_code),), "tushare-dividend-v1"
    )
    response = transport.request(query, credential=credential)
    ref = store.put(
        response.exact_bytes,
        RawArtifactMetadata(
            "tushare-pro",
            {"query_identity": query.identity},
            datetime.fromisoformat(response.fetched_at_iso),
            "tushare-dividend",
            "v1",
        ),
    )
    rows = parse_rows(store.read(ref.artifact_id), DIVIDEND_FIELDS)
    actions: list[CorporateActionType] = []
    try:
        for row in rows:
            common = _common(row)
            cash, bonus, transfer = (
                Decimal(row["cash_div_tax"]),
                Decimal(row["stk_bo_rate"]),
                Decimal(row["stk_co_rate"]),
            )
            if Decimal(row["stk_div"]) != bonus + transfer:
                raise ValueError("stk_div total mismatch")
            if cash > 0:
                actions.append(
                    CashDividend(
                        *common,
                        _date(row["pay_date"]),
                        cash,
                        ref.artifact_id,
                        "tushare-dividend-v1",
                    )
                )
            if bonus + transfer > 0:
                actions.append(
                    BonusShareEvent(
                        *common,
                        _date(row["div_listdate"]),
                        bonus,
                        transfer,
                        ref.artifact_id,
                        "tushare-dividend-v1",
                    )
                )
    except (TypeError, ValueError) as exc:
        raise TerminalProviderError(
            "invalid official dividend mapping or dates"
        ) from exc
    ids = tuple(action.event_id for action in actions)
    if len(ids) != len(set(ids)):
        raise TerminalProviderError("duplicate corporate action identity")
    return CorporateActionBatch(
        (ref,), tuple(sorted(actions, key=lambda action: action.event_id))
    )


def acquire_tushare_rights(*args: object, **kwargs: object) -> None:
    del args, kwargs
    raise CapabilityUnavailableError(
        "Tushare rights history capability is not verified"
    )


def _common(row: Dict[str, str]) -> Tuple[SecurityId, date, date, date]:
    return (
        SecurityId.parse(_canonical_code(row["ts_code"])),
        _date(row["ann_date"]),
        _date(row["record_date"]),
        _date(row["ex_date"]),
    )


def _date(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()
