"""Raw-first Tushare security master including inactive identities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

from stock_quant.data import RawArtifactMetadata, RawArtifactRef, RawArtifactStore
from stock_quant.domain import ListingLifecycle, SecurityId
from stock_quant.provider.api import (
    ProviderQuery,
    ProviderTransport,
    TerminalProviderError,
)
from stock_quant.provider.tushare import _canonical_code, parse_rows
from stock_quant.universe import SecurityMaster, SecurityMetadata


FIELDS = ("delist_date", "list_date", "list_status", "name", "ts_code")


@dataclass(frozen=True)
class SecurityMasterBatch:
    raw: RawArtifactRef
    master: SecurityMaster
    lifecycles: Tuple[ListingLifecycle, ...]


def acquire_security_master(
    transport: ProviderTransport, store: RawArtifactStore, *, credential: str
) -> SecurityMasterBatch:
    query = ProviderQuery(
        "stock_basic", FIELDS, (("list_status", "ALL"),), "tushare-stock-basic-v1"
    )
    response = transport.request(query, credential=credential)
    ref = store.put(
        response.exact_bytes,
        RawArtifactMetadata(
            "tushare-pro",
            {"query_identity": query.identity},
            datetime.fromisoformat(response.fetched_at_iso),
            "tushare-stock-basic",
            "v1",
        ),
    )
    rows = parse_rows(store.read(ref.artifact_id), FIELDS)
    metadata, lifecycles = [], []
    try:
        for row in rows:
            security = SecurityId.parse(_canonical_code(row["ts_code"]))
            listed = datetime.strptime(row["list_date"], "%Y%m%d").date()
            raw_delist = row["delist_date"]
            delisted = (
                None
                if raw_delist in ("", "None")
                else datetime.strptime(raw_delist, "%Y%m%d").date()
            )
            metadata.append(SecurityMetadata(security, row["name"]))
            lifecycles.append(ListingLifecycle(security, listed, delisted))
    except (TypeError, ValueError) as exc:
        raise TerminalProviderError(
            "invalid security master chronology or mapping"
        ) from exc
    return SecurityMasterBatch(
        ref,
        SecurityMaster(metadata),
        tuple(sorted(lifecycles, key=lambda row: row.security_id)),
    )
