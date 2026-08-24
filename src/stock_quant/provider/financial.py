"""Raw-first financial observations with announcement and observed revision time."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Tuple

from stock_quant.data import RawArtifactMetadata, RawArtifactRef, RawArtifactStore
from stock_quant.domain import SecurityId
from stock_quant.provider.api import (
    ProviderQuery,
    ProviderTransport,
    TerminalProviderError,
)
from stock_quant.provider.tushare import _canonical_code, parse_rows


FIELDS = ("ann_date", "end_date", "n_income", "revenue", "ts_code", "update_flag")


@dataclass(frozen=True)
class FinancialObservation:
    security_id: SecurityId
    report_period: date
    announcement_date: date
    revision_observed_at: datetime
    update_flag: str
    net_income: Optional[Decimal]
    revenue: Optional[Decimal]
    raw_identity: str


def acquire_financials(
    transport: ProviderTransport,
    store: RawArtifactStore,
    *,
    credential: str,
    ts_code: str,
) -> Tuple[RawArtifactRef, Tuple[FinancialObservation, ...]]:
    query = ProviderQuery(
        "income", FIELDS, (("ts_code", ts_code),), "tushare-income-v1"
    )
    response = transport.request(query, credential=credential)
    fetched = datetime.fromisoformat(response.fetched_at_iso)
    ref = store.put(
        response.exact_bytes,
        RawArtifactMetadata(
            "tushare-pro",
            {"query_identity": query.identity},
            fetched,
            "tushare-income",
            "v1",
        ),
    )
    rows = parse_rows(store.read(ref.artifact_id), FIELDS)
    output = []
    try:
        for row in rows:
            if row["ann_date"] in ("", "None"):
                raise ValueError
            output.append(
                FinancialObservation(
                    SecurityId.parse(_canonical_code(row["ts_code"])),
                    _date(row["end_date"]),
                    _date(row["ann_date"]),
                    fetched,
                    row["update_flag"],
                    _optional_decimal(row["n_income"]),
                    _optional_decimal(row["revenue"]),
                    ref.artifact_id,
                )
            )
    except (TypeError, ValueError) as exc:
        raise TerminalProviderError(
            "financial announcement and report period are required"
        ) from exc
    keys = tuple(
        (row.security_id, row.report_period, row.announcement_date, row.update_flag)
        for row in output
    )
    if len(keys) != len(set(keys)):
        raise TerminalProviderError("duplicate financial revision")
    return ref, tuple(
        sorted(
            output,
            key=lambda row: (
                row.security_id,
                row.report_period,
                row.announcement_date,
                row.update_flag,
            ),
        )
    )


def _date(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()


def _optional_decimal(value: str) -> Optional[Decimal]:
    return None if value in ("", "None") else Decimal(value)
