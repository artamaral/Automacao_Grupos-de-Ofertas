from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from ofertas_bot.models import MessageDraft
from ofertas_bot.storage.json_message_draft_store import (
    message_draft_from_json,
    message_draft_to_json,
)

ReviewStatus = Literal["pending", "approved", "rejected"]
VALID_REVIEW_STATUSES = {"pending", "approved", "rejected"}


class MessageReviewQueueStoreError(ValueError):
    """Raised when local message review queue storage cannot parse saved data."""


class MessageReviewQueueStoreWriteError(OSError):
    """Raised when local message review queue storage cannot write data."""


class MessageReviewQueueUpdateError(ValueError):
    """Raised when a review queue item cannot be updated."""


@dataclass(frozen=True)
class MessageReviewQueueItem:
    draft: MessageDraft
    status: ReviewStatus = "pending"
    reviewer: str | None = None
    notes: str = ""


class JsonMessageReviewQueueStore:
    """Optional local JSON storage for human review of message drafts."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, items: tuple[MessageReviewQueueItem, ...]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = [message_review_queue_item_to_json(item) for item in items]
            self.path.write_text(
                json.dumps(payload, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            msg = f"Could not write message review queue JSON to {self.path}"
            raise MessageReviewQueueStoreWriteError(msg) from error

    def load(self) -> tuple[MessageReviewQueueItem, ...]:
        if not self.path.exists():
            return ()

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            msg = "Saved message review queue JSON is invalid"
            raise MessageReviewQueueStoreError(msg) from error

        if not isinstance(payload, list):
            msg = "Saved message review queue JSON must contain a list"
            raise MessageReviewQueueStoreError(msg)

        return tuple(message_review_queue_item_from_json(item) for item in payload)


def create_pending_review_queue(
    drafts: tuple[MessageDraft, ...],
) -> tuple[MessageReviewQueueItem, ...]:
    return tuple(MessageReviewQueueItem(draft=draft) for draft in drafts)


def approved_review_drafts(
    items: tuple[MessageReviewQueueItem, ...],
) -> tuple[MessageDraft, ...]:
    return tuple(item.draft for item in items if item.status == "approved")


def approve_review_queue_item(
    items: tuple[MessageReviewQueueItem, ...],
    item_number: int,
    reviewer: str,
    notes: str = "",
) -> tuple[MessageReviewQueueItem, ...]:
    return mark_review_queue_item(
        items=items,
        item_number=item_number,
        status="approved",
        reviewer=reviewer,
        notes=notes,
    )


def reject_review_queue_item(
    items: tuple[MessageReviewQueueItem, ...],
    item_number: int,
    reviewer: str,
    notes: str = "",
) -> tuple[MessageReviewQueueItem, ...]:
    return mark_review_queue_item(
        items=items,
        item_number=item_number,
        status="rejected",
        reviewer=reviewer,
        notes=notes,
    )


def mark_review_queue_item(
    items: tuple[MessageReviewQueueItem, ...],
    item_number: int,
    status: ReviewStatus,
    reviewer: str,
    notes: str = "",
) -> tuple[MessageReviewQueueItem, ...]:
    if item_number < 1 or item_number > len(items):
        msg = "Review queue item number is out of range"
        raise MessageReviewQueueUpdateError(msg)

    updated_items = list(items)
    original = updated_items[item_number - 1]
    updated_items[item_number - 1] = MessageReviewQueueItem(
        draft=original.draft,
        status=status,
        reviewer=_clean_reviewer(reviewer),
        notes=notes.strip(),
    )
    return tuple(updated_items)


def message_review_queue_item_to_json(
    item: MessageReviewQueueItem,
) -> dict[str, Any]:
    return {
        "draft": message_draft_to_json(item.draft),
        "status": item.status,
        "reviewer": item.reviewer,
        "notes": item.notes,
    }


def message_review_queue_item_from_json(data: object) -> MessageReviewQueueItem:
    if not isinstance(data, dict):
        msg = "Saved message review queue item must be an object"
        raise MessageReviewQueueStoreError(msg)

    try:
        raw_status = str(data["status"])
        if raw_status not in VALID_REVIEW_STATUSES:
            msg = "Saved message review queue status is invalid"
            raise MessageReviewQueueStoreError(msg)
        status = cast(ReviewStatus, raw_status)
        return MessageReviewQueueItem(
            draft=message_draft_from_json(data["draft"]),
            status=status,
            reviewer=_optional_str(data.get("reviewer")),
            notes=str(data.get("notes", "")),
        )
    except (KeyError, TypeError, ValueError) as error:
        msg = "Saved message review queue item is invalid"
        raise MessageReviewQueueStoreError(msg) from error


def _clean_reviewer(value: str) -> str | None:
    clean_value = value.strip()
    if not clean_value:
        return None
    return clean_value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
