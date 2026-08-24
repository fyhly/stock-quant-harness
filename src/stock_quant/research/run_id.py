"""Collision-safe canonical research run IDs and append-only registry."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import secrets
from typing import Optional

_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{12}Z-[0-9a-f]{32}$")


class RunRegistryError(RuntimeError):
    pass


@dataclass(frozen=True, order=True)
class RunId:
    value: str

    def __post_init__(self) -> None:
        if not _PATTERN.fullmatch(self.value):
            raise ValueError("invalid canonical run_id")

    @classmethod
    def generate(cls, now: Optional[datetime] = None) -> "RunId":
        instant = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        return cls(instant.strftime("%Y%m%dT%H%M%S%fZ-") + secrets.token_hex(16))


@dataclass(frozen=True)
class RunRecord:
    run_id: RunId
    status: str
    created_at: str


class RunRegistry:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def register(self, run_id: RunId, created_at: datetime) -> RunRecord:
        if created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        target = self.root / run_id.value
        try:
            target.mkdir()
        except FileExistsError as exc:
            raise RunRegistryError("run_id already registered") from exc
        record = RunRecord(
            run_id, "CREATED", created_at.astimezone(timezone.utc).isoformat()
        )
        (target / "000-created.json").write_text(
            json.dumps(
                {
                    "run_id": run_id.value,
                    "status": record.status,
                    "created_at": record.created_at,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return record

    def lookup(self, run_id: RunId) -> RunRecord:
        try:
            raw = json.loads(
                (self.root / run_id.value / "000-created.json").read_text()
            )
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise RunRegistryError("run_id missing or corrupt") from exc
        return RunRecord(run_id, raw["status"], raw["created_at"])
