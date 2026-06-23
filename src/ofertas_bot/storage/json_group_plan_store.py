from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ofertas_bot.group_plan import GroupPlan, summarize_group_plans


class GroupPlanStoreError(ValueError):
    """Raised when local group plan storage cannot parse saved data."""


class GroupPlanStoreWriteError(OSError):
    """Raised when local group plan storage cannot write data."""


class JsonGroupPlanStore:
    """Optional local JSON storage for summarized group plans."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, summary: dict[str, Any]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            msg = f"Could not write group plan JSON to {self.path}"
            raise GroupPlanStoreWriteError(msg) from error

    def save_plans(self, plans: tuple[GroupPlan, ...]) -> None:
        self.save(summarize_group_plans(plans))

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            msg = "Saved group plan JSON is invalid"
            raise GroupPlanStoreError(msg) from error

        if not isinstance(payload, dict):
            msg = "Saved group plan JSON must contain an object"
            raise GroupPlanStoreError(msg)

        return payload
