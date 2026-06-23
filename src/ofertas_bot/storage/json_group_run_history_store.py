from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ofertas_bot.group_plan import GroupPlan


class GroupRunHistoryStoreError(ValueError):
    """Raised when local group run history cannot be parsed."""


class GroupRunHistoryStoreWriteError(OSError):
    """Raised when local group run history cannot be written."""


class JsonGroupRunHistoryStore:
    """Optional local JSON storage for the last run per group."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, history: dict[str, datetime | None]) -> None:
        payload = {
            _normalize_slug(slug): value.isoformat() if value else None
            for slug, value in history.items()
            if _normalize_slug(slug)
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            msg = f"Could not write group run history JSON to {self.path}"
            raise GroupRunHistoryStoreWriteError(msg) from error

    def load(self) -> dict[str, datetime | None]:
        if not self.path.exists():
            return {}

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            msg = "Saved group run history JSON is invalid"
            raise GroupRunHistoryStoreError(msg) from error

        if not isinstance(payload, dict):
            msg = "Saved group run history JSON must contain an object"
            raise GroupRunHistoryStoreError(msg)

        return {
            _normalize_slug(slug): _parse_optional_datetime(value)
            for slug, value in payload.items()
            if _normalize_slug(slug)
        }

    def update_allowed_runs(
        self,
        *,
        plans: tuple[GroupPlan, ...],
        ran_at: datetime,
    ) -> dict[str, datetime | None]:
        history = self.load()
        for plan in plans:
            if plan.allowed:
                history[plan.group_slug] = ran_at
        self.save(history)
        return history


def _normalize_slug(value: object) -> str:
    return str(value).strip().lower()


def _parse_optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        msg = "Saved group run history values must be ISO datetimes or null"
        raise GroupRunHistoryStoreError(msg)
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        msg = "Saved group run history datetime is invalid"
        raise GroupRunHistoryStoreError(msg) from error
