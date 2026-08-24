"""Historical membership ingestion that refuses current-state backfill."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Tuple

from stock_quant.data import RawArtifactMetadata, RawArtifactRef, RawArtifactStore
from stock_quant.domain import SecurityId
from stock_quant.provider.api import (
    ProviderQuery,
    ProviderTransport,
    TerminalProviderError,
)
from stock_quant.provider.tushare import _canonical_code, parse_rows


class CapabilityUnavailableError(TerminalProviderError):
    pass


@dataclass(frozen=True)
class EffectiveHistoryRecord:
    subject_id: str
    security_id: SecurityId
    effective_from: date
    effective_to: Optional[date]
    raw_identity: str


def acquire_effective_history(
    transport: ProviderTransport,
    store: RawArtifactStore,
    *,
    credential: str,
    endpoint: str,
    subject_field: str,
) -> Tuple[RawArtifactRef, Tuple[EffectiveHistoryRecord, ...]]:
    fields = tuple(sorted((subject_field, "ts_code", "effective_from", "effective_to")))
    query = ProviderQuery(endpoint, fields, (), f"tushare-{endpoint}-history-v1")
    response = transport.request(query, credential=credential)
    ref = store.put(
        response.exact_bytes,
        RawArtifactMetadata(
            "tushare-pro",
            {"query_identity": query.identity},
            datetime.fromisoformat(response.fetched_at_iso),
            f"tushare-{endpoint}",
            "history-v1",
        ),
    )
    try:
        rows = parse_rows(store.read(ref.artifact_id), fields)
    except TerminalProviderError as exc:
        raise CapabilityUnavailableError(
            "source lacks effective-dated history capability"
        ) from exc
    output = []
    try:
        for row in rows:
            start = datetime.strptime(row["effective_from"], "%Y%m%d").date()
            raw_end = row["effective_to"]
            end = (
                None
                if raw_end in ("", "None")
                else datetime.strptime(raw_end, "%Y%m%d").date()
            )
            if end is not None and end <= start:
                raise ValueError
            output.append(
                EffectiveHistoryRecord(
                    row[subject_field],
                    SecurityId.parse(_canonical_code(row["ts_code"])),
                    start,
                    end,
                    ref.artifact_id,
                )
            )
    except (KeyError, TypeError, ValueError) as exc:
        raise CapabilityUnavailableError("source history dates are invalid") from exc
    keys = tuple(
        (row.subject_id, row.security_id, row.effective_from) for row in output
    )
    if len(keys) != len(set(keys)):
        raise TerminalProviderError("duplicate effective history")
    return ref, tuple(
        sorted(
            output,
            key=lambda row: (row.subject_id, row.security_id, row.effective_from),
        )
    )
