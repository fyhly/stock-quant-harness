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
from stock_quant.provider.history import (
    acquire_effective_history,
    CapabilityUnavailableError,
    EffectiveHistoryRecord,
)
from stock_quant.provider.actions import acquire_corporate_actions, CorporateActionBatch
from stock_quant.provider.financial import acquire_financials, FinancialObservation

__all__ = [
    "acquire_daily",
    "acquire_corporate_actions",
    "acquire_financials",
    "acquire_security_master",
    "acquire_effective_history",
    "CapabilityUnavailableError",
    "FakeTransport",
    "ProviderError",
    "ProviderQuery",
    "ProviderResponse",
    "ProviderTransport",
    "redact",
    "RetryableProviderError",
    "TerminalProviderError",
    "SecurityMasterBatch",
    "EffectiveHistoryRecord",
    "CorporateActionBatch",
    "FinancialObservation",
]
