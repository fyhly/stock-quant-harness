"""Raw-first Tushare Pro official response-schema adapters."""

from datetime import datetime
from decimal import Decimal
import json
from typing import Dict, Iterable, Tuple

from stock_quant.data import (
    DailyBar,
    DailyBarSeries,
    RawArtifactMetadata,
    RawArtifactRef,
    RawArtifactStore,
)
from stock_quant.domain import SecurityId, TradingDay
from stock_quant.provider.api import (
    ProviderQuery,
    ProviderTransport,
    TerminalProviderError,
)


DAILY_FIELDS = (
    "amount",
    "close",
    "high",
    "low",
    "open",
    "trade_date",
    "ts_code",
    "vol",
)


def acquire_daily(
    transport: ProviderTransport,
    store: RawArtifactStore,
    *,
    credential: str,
    ts_code: str,
    start_date: str,
    end_date: str,
) -> Tuple[RawArtifactRef, DailyBarSeries]:
    query = ProviderQuery(
        "daily",
        DAILY_FIELDS,
        tuple(
            sorted(
                (
                    ("end_date", end_date),
                    ("start_date", start_date),
                    ("ts_code", ts_code),
                )
            )
        ),
        "tushare-daily-v1",
    )
    response = transport.request(query, credential=credential)
    fetched_at = datetime.fromisoformat(response.fetched_at_iso)
    metadata = RawArtifactMetadata(
        "tushare-pro",
        {"query_identity": query.identity},
        fetched_at,
        "tushare-daily",
        "v1",
    )
    ref = store.put(response.exact_bytes, metadata)
    rows = parse_rows(store.read(ref.artifact_id), DAILY_FIELDS)
    bars = []
    for row in rows:
        security = SecurityId.parse(_canonical_code(row["ts_code"]))
        volume = Decimal(row["vol"]) * Decimal(100)
        if volume != volume.to_integral_value():
            raise TerminalProviderError(
                "daily vol cannot convert exactly from lots to shares"
            )
        bars.append(
            DailyBar(
                security,
                TradingDay(datetime.strptime(row["trade_date"], "%Y%m%d").date()),
                Decimal(row["open"]),
                Decimal(row["high"]),
                Decimal(row["low"]),
                Decimal(row["close"]),
                int(volume),
                Decimal(row["amount"]) * Decimal(1000),
            )
        )
    bars.sort(key=lambda bar: bar.trading_day)
    if not bars:
        raise TerminalProviderError("daily response is empty")
    try:
        return ref, DailyBarSeries(bars[0].security_id, bars)
    except (TypeError, ValueError) as exc:
        raise TerminalProviderError("invalid or duplicate daily rows") from exc


def parse_rows(
    content: bytes, expected_fields: Iterable[str]
) -> Tuple[Dict[str, str], ...]:
    try:
        payload = json.loads(content)
        if payload["code"] != 0 or payload.get("msg") not in (None, ""):
            raise TerminalProviderError("Tushare returned an error payload")
        fields = payload["data"]["fields"]
        items = payload["data"]["items"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise TerminalProviderError("invalid Tushare response envelope") from exc
    if set(fields) != set(expected_fields) or len(fields) != len(set(fields)):
        raise TerminalProviderError("Tushare response schema drift")
    if any(not isinstance(item, list) or len(item) != len(fields) for item in items):
        raise TerminalProviderError("Tushare response row width mismatch")
    return tuple(
        {field: str(value) for field, value in zip(fields, item)} for item in items
    )


def _canonical_code(value: str) -> str:
    try:
        code, suffix = value.split(".")
        mic = {"SH": "XSHG", "SZ": "XSHE"}[suffix]
    except (ValueError, KeyError) as exc:
        raise TerminalProviderError("unsupported Tushare ts_code") from exc
    return f"{code}.{mic}"
