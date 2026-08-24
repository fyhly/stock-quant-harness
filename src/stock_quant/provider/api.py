"""Injected transport and credential-safe provider contracts."""

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Protocol, Tuple


class ProviderError(RuntimeError):
    retryable = False


class RetryableProviderError(ProviderError):
    retryable = True


class TerminalProviderError(ProviderError):
    pass


@dataclass(frozen=True)
class ProviderQuery:
    endpoint: str
    fields: Tuple[str, ...]
    params: Tuple[Tuple[str, str], ...]
    schema_version: str
    base_url: str = "https://api.tushare.pro"

    def __post_init__(self) -> None:
        if not self.endpoint.strip() or not self.schema_version.strip():
            raise ValueError("endpoint and schema version are required")
        if not self.base_url.startswith("https://"):
            raise ValueError("provider transport requires an HTTPS base URL")
        if self.fields != tuple(sorted(set(self.fields))) or self.params != tuple(
            sorted(set(self.params))
        ):
            raise ValueError("fields and params must be sorted and unique")

    @property
    def identity(self) -> str:
        payload = json.dumps(
            {
                "endpoint": self.endpoint,
                "fields": self.fields,
                "params": self.params,
                "schema": self.schema_version,
                "base_url": self.base_url,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class ProviderResponse:
    exact_bytes: bytes
    fetched_at_iso: str


class ProviderTransport(Protocol):
    def request(self, query: ProviderQuery, *, credential: str) -> ProviderResponse: ...


class FakeTransport:
    def __init__(self, responses: Mapping[str, bytes]) -> None:
        self._responses = dict(responses)
        self.queries: list[ProviderQuery] = []

    def request(self, query: ProviderQuery, *, credential: str) -> ProviderResponse:
        if not credential:
            raise TerminalProviderError("missing runtime credential")
        self.queries.append(query)
        try:
            return ProviderResponse(
                self._responses[query.endpoint], "2024-01-01T00:00:00+00:00"
            )
        except KeyError as exc:
            raise RetryableProviderError("fake response unavailable") from exc


def redact(value: Any, secrets: Tuple[str, ...]) -> str:
    rendered = str(value)
    for secret in secrets:
        if secret:
            rendered = rendered.replace(secret, "[REDACTED]")
    return rendered
