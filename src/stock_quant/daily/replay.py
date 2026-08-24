"""Exact offline reconstruction of covered immutable daily reports."""

from dataclasses import dataclass
from datetime import date
import hashlib
from typing import Callable, Mapping, Tuple

from stock_quant.daily.report import DailyResearchReport


class DailyReplayError(RuntimeError):
    pass


@dataclass(frozen=True)
class DailyReplaySpec:
    report_date: date
    covered_dates: Tuple[date, ...]
    pinned_identities: Tuple[Tuple[str, str], ...]
    pinned_inputs: Tuple[Tuple[str, str], ...]
    expected_fingerprint: str


@dataclass(frozen=True)
class DailyReplayResult:
    report_date: date
    fingerprint: str
    exact: bool


def replay_daily_report(
    spec: DailyReplaySpec,
    *,
    current_identities: Mapping[str, str],
    load_local: Callable[[str], bytes],
    reconstruct: Callable[[Mapping[str, bytes]], DailyResearchReport],
) -> DailyReplayResult:
    if spec.report_date not in spec.covered_dates:
        raise DailyReplayError("daily replay date is outside local coverage")
    pinned = dict(spec.pinned_identities)
    if current_identities != pinned:
        raise DailyReplayError("daily replay identity drift")
    inputs = {}
    try:
        for name, expected in spec.pinned_inputs:
            raw = load_local(name)
            if hashlib.sha256(raw).hexdigest() != expected:
                raise DailyReplayError(f"daily replay input tamper: {name}")
            inputs[name] = raw
    except DailyReplayError:
        raise
    except Exception as exc:
        raise DailyReplayError("daily replay pinned input missing") from exc
    report = reconstruct(inputs)
    if report.fingerprint != spec.expected_fingerprint:
        raise DailyReplayError("daily report fingerprint mismatch")
    return DailyReplayResult(spec.report_date, report.fingerprint, True)
