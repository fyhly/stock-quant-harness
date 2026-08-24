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
from stock_quant.provider.master import acquire_security_master, SecurityMasterBatch

__all__ = [
    "acquire_daily",
    "acquire_security_master",
    "FakeTransport",
    "ProviderError",
    "ProviderQuery",
    "ProviderResponse",
    "ProviderTransport",
    "redact",
    "RetryableProviderError",
    "TerminalProviderError",
    "SecurityMasterBatch",
]
