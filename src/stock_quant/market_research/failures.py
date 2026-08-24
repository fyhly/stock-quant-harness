"""Append-only batch failure evidence and offline reconciled summary."""

from dataclasses import asdict, dataclass
from html import escape
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Iterable

from stock_quant.market_research.runner import MarketBatchResult, MarketItemRecord


_SHA = re.compile(r"^[0-9a-f]{64}$")


class FailureRegistryError(RuntimeError):
    pass


@dataclass(frozen=True)
class FailureEvidence:
    failure_id: str
    item_id: str
    research_date: str
    security_id: str
    failure_type: str
    failure_message: str
    run_identity: str
    data_identity: str
    git_identity: str
    config_identity: str


class FailureRegistry:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def retain(
        self,
        record: MarketItemRecord,
        *,
        run_identity: str,
        data_identity: str,
        git_identity: str,
        config_identity: str,
    ) -> FailureEvidence:
        if record.succeeded:
            raise FailureRegistryError("cannot register a successful item as failure")
        identities = (run_identity, data_identity, git_identity, config_identity)
        if any(not _SHA.fullmatch(value) for value in identities):
            raise FailureRegistryError("failure identities must be SHA-256")
        fields = {
            "item_id": record.item_id,
            "research_date": record.item.research_date.isoformat(),
            "security_id": str(record.item.security_id),
            "failure_type": record.failure_type,
            "failure_message": record.failure_message,
            "run_identity": run_identity,
            "data_identity": data_identity,
            "git_identity": git_identity,
            "config_identity": config_identity,
        }
        failure_id = hashlib.sha256(_json(fields)).hexdigest()
        evidence = FailureEvidence(failure_id, **fields)
        raw = _json(asdict(evidence))
        target = self.root / f"{failure_id}.json"
        descriptor, temp_name = tempfile.mkstemp(prefix=".failure-", dir=self.root)
        temp = Path(temp_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temp, target)
            except FileExistsError:
                if target.read_bytes() != raw:
                    raise FailureRegistryError("failure record collision or tamper")
        finally:
            temp.unlink(missing_ok=True)
        return evidence

    def read(self, failure_id: str) -> FailureEvidence:
        if not _SHA.fullmatch(failure_id):
            raise FailureRegistryError("invalid failure identity")
        try:
            payload = json.loads((self.root / f"{failure_id}.json").read_text())
            evidence = FailureEvidence(**payload)
        except (FileNotFoundError, json.JSONDecodeError, TypeError) as exc:
            raise FailureRegistryError("failure record missing or invalid") from exc
        expected = hashlib.sha256(
            _json(
                {
                    key: value
                    for key, value in asdict(evidence).items()
                    if key != "failure_id"
                }
            )
        ).hexdigest()
        if evidence.failure_id != failure_id or expected != failure_id:
            raise FailureRegistryError("failure record tampered")
        return evidence


def render_market_summary(
    batch: MarketBatchResult, failures: Iterable[FailureEvidence]
) -> str:
    retained = tuple(sorted(failures, key=lambda item: item.failure_id))
    failed_item_ids = tuple(
        sorted(record.item_id for record in batch.records if not record.succeeded)
    )
    if batch.total != batch.succeeded + batch.failed or batch.failed != len(retained):
        raise FailureRegistryError("batch totals do not reconcile")
    if failed_item_ids != tuple(sorted(item.item_id for item in retained)):
        raise FailureRegistryError("retained failures do not match failed batch items")
    details = (
        "".join(
            "<li>"
            + escape(
                f"{item.research_date} {item.security_id} "
                f"{item.failure_type}: {item.failure_message}"
            )
            + "</li>"
            for item in retained
        )
        or "<li>None</li>"
    )
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>Market research summary</title>'
        "<style>body{font-family:sans-serif}.warning{font-weight:bold;color:#900}</style>"
        "</head><body><h1>Full-market research summary</h1>"
        '<p class="warning">RESEARCH ONLY</p>'
        f"<p>Manifest: {escape(batch.manifest_identity)}</p>"
        f"<p>Total: {batch.total}; succeeded: {batch.succeeded}; failed: {batch.failed}</p>"
        f"<h2>Failures</h2><ul>{details}</ul><h2>Limitations</h2>"
        "<p>No winner selection or out-of-sample claim.</p></body></html>"
    )


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
