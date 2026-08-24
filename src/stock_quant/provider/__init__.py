"""Offline-testable external data acquisition adapters."""

from stock_quant.provider.api import (
    FakeTransport,
    ProviderError,
    ProviderQuery,
    ProviderResponse,
    ProviderTransport,
    redact,
    RetryableProviderError,
    TerminalProviderError,
)
from stock_quant.provider.tushare import acquire_daily

__all__ = [
    "acquire_daily",
    "FakeTransport",
    "ProviderError",
    "ProviderQuery",
    "ProviderResponse",
    "ProviderTransport",
    "redact",
    "RetryableProviderError",
    "TerminalProviderError",
]
