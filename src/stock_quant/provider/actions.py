"""Raw-first official dividend and rights response ingestion."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Tuple

from stock_quant.actions import (
    BonusShareEvent,
    CashDividend,
    RightsIssue,
)
from stock_quant.actions.model import CorporateActionType
from stock_quant.data import RawArtifactMetadata, RawArtifactRef, RawArtifactStore
from stock_quant.domain import SecurityId
from stock_quant.provider.api import (
    ProviderQuery,
    ProviderTransport,
    TerminalProviderError,
)
from stock_quant.provider.tushare import _canonical_code, parse_rows


DIVIDEND_FIELDS = (
    "ann_date",
    "cash_div_tax",
    "ex_date",
    "pay_date",
    "record_date",
    "stk_bo_rate",
    "stk_div",
    "ts_code",
)
RIGHTS_FIELDS = (
    "ann_date",
    "ex_date",
    "pay_date",
    "record_date",
    "rights_price",
    "rights_ratio",
    "ts_code",
)


@dataclass(frozen=True)
class CorporateActionBatch:
    raw_refs: Tuple[RawArtifactRef, RawArtifactRef]
    actions: Tuple[CorporateActionType, ...]


def acquire_corporate_actions(
    transport: ProviderTransport,
    store: RawArtifactStore,
    *,
    credential: str,
    ts_code: str,
) -> CorporateActionBatch:
    refs = []
    grouped = []
    for endpoint, fields in (
        ("dividend", DIVIDEND_FIELDS),
        ("rights_issue", RIGHTS_FIELDS),
    ):
        query = ProviderQuery(
            endpoint, fields, (("ts_code", ts_code),), f"tushare-{endpoint}-v1"
        )
        response = transport.request(query, credential=credential)
        ref = store.put(
            response.exact_bytes,
            RawArtifactMetadata(
                "tushare-pro",
                {"query_identity": query.identity},
                datetime.fromisoformat(response.fetched_at_iso),
                f"tushare-{endpoint}",
                "v1",
            ),
        )
        refs.append(ref)
        grouped.append(parse_rows(store.read(ref.artifact_id), fields))
    actions: list[CorporateActionType] = []
    try:
        for row in grouped[0]:
            common = _common(row)
            cash, bonus, transfer = (
                Decimal(row["cash_div_tax"]),
                Decimal(row["stk_div"]),
                Decimal(row["stk_bo_rate"]),
            )
            if cash > 0:
                actions.append(
                    CashDividend(
                        *common,
                        _date(row["pay_date"]),
                        cash,
                        refs[0].artifact_id,
                        "tushare-dividend-v1",
                    )
                )
            if bonus + transfer > 0:
                actions.append(
                    BonusShareEvent(
                        *common,
                        _date(row["pay_date"]),
                        bonus,
                        transfer,
                        refs[0].artifact_id,
                        "tushare-dividend-v1",
                    )
                )
        for row in grouped[1]:
            actions.append(
                RightsIssue(
                    *_common(row),
                    _date(row["pay_date"]),
                    Decimal(row["rights_ratio"]),
                    Decimal(row["rights_price"]),
                    refs[1].artifact_id,
                    "tushare-rights-v1",
                )
            )
    except (TypeError, ValueError) as exc:
        raise TerminalProviderError(
            "invalid or missing corporate-action dates"
        ) from exc
    ids = tuple(action.event_id for action in actions)
    if len(ids) != len(set(ids)):
        raise TerminalProviderError("duplicate corporate action identity")
    return CorporateActionBatch(
        (refs[0], refs[1]), tuple(sorted(actions, key=lambda action: action.event_id))
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
