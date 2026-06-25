from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from ofertas_bot.group_profiles import DEFAULT_GROUP_PROFILES, GroupProfileCatalog
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


class MessageReviewQueueSummary(TypedDict):
    total: int
    pending: int
    approved: int
    rejected: int
    routed: int
    unrouted: int


class MessageReviewQueueGroupSummary(TypedDict):
    group_slug: str
    total: int
    pending: int
    approved: int
    rejected: int


@dataclass(frozen=True)
class MessageReviewRouting:
    group_slug: str
    group_name: str
    destination_kind: str
    destination_ref: str | None
    message_tone: str
    channel_adapter: str = "whatsapp"
    max_messages_per_run: int = 0
    min_interval_seconds: int = 0


@dataclass(frozen=True)
class MessageReviewQueueItem:
    draft: MessageDraft
    status: ReviewStatus = "pending"
    reviewer: str | None = None
    notes: str = ""
    routing: MessageReviewRouting | None = None


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
    group_catalog: GroupProfileCatalog = DEFAULT_GROUP_PROFILES,
) -> tuple[MessageReviewQueueItem, ...]:
    items: list[MessageReviewQueueItem] = []
    for draft in drafts:
        matching_profiles = tuple(
            profile
            for profile in group_catalog.active_profiles()
            if profile.allows_niche(draft.offer.niche)
            and profile.allows_marketplace(draft.offer.marketplace)
        )
        if not matching_profiles:
            items.append(MessageReviewQueueItem(draft=draft))
            continue
        for profile in matching_profiles:
            for destination in profile.destinations:
                if not destination.active:
                    continue
                items.append(
                    MessageReviewQueueItem(
                        draft=draft,
                        routing=MessageReviewRouting(
                            group_slug=profile.slug,
                            group_name=profile.name,
                            destination_kind=destination.destination_kind,
                            destination_ref=destination.destination_ref,
                            channel_adapter=destination.channel_adapter,
                            message_tone=profile.message_tone,
                            max_messages_per_run=destination.max_messages_per_run
                            or profile.max_offers_per_run,
                            min_interval_seconds=destination.min_interval_seconds,
                        ),
                    )
                )
    return tuple(items)


def approved_review_drafts(
    items: tuple[MessageReviewQueueItem, ...],
) -> tuple[MessageDraft, ...]:
    return tuple(item.draft for item in items if item.status == "approved")


def filter_review_queue_items(
    items: tuple[MessageReviewQueueItem, ...],
    *,
    group_slug: str | None = None,
) -> tuple[MessageReviewQueueItem, ...]:
    if group_slug is None:
        return items
    normalized_group_slug = group_slug.strip().lower()
    return tuple(
        item
        for item in items
        if item.routing is not None and item.routing.group_slug == normalized_group_slug
    )


def summarize_review_queue(
    items: tuple[MessageReviewQueueItem, ...],
) -> MessageReviewQueueSummary:
    summary: MessageReviewQueueSummary = {
        "total": len(items),
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "routed": 0,
        "unrouted": 0,
    }
    for item in items:
        summary[item.status] += 1
        if item.routing is None:
            summary["unrouted"] += 1
        else:
            summary["routed"] += 1
    return summary


def summarize_review_queue_by_group(
    items: tuple[MessageReviewQueueItem, ...],
) -> tuple[MessageReviewQueueGroupSummary, ...]:
    grouped: dict[str, MessageReviewQueueGroupSummary] = {}
    for item in items:
        group_slug = item.routing.group_slug if item.routing is not None else "__sem_rota__"
        if group_slug not in grouped:
            grouped[group_slug] = {
                "group_slug": group_slug,
                "total": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
            }
        grouped[group_slug]["total"] += 1
        grouped[group_slug][item.status] += 1
    return tuple(grouped[key] for key in sorted(grouped))


def approve_review_queue_item(
    items: tuple[MessageReviewQueueItem, ...],
    item_number: int,
    reviewer: str,
    notes: str = "",
    group_slug: str | None = None,
) -> tuple[MessageReviewQueueItem, ...]:
    return mark_review_queue_item(
        items=items,
        item_number=item_number,
        status="approved",
        reviewer=reviewer,
        notes=notes,
        group_slug=group_slug,
    )


def reject_review_queue_item(
    items: tuple[MessageReviewQueueItem, ...],
    item_number: int,
    reviewer: str,
    notes: str = "",
    group_slug: str | None = None,
) -> tuple[MessageReviewQueueItem, ...]:
    return mark_review_queue_item(
        items=items,
        item_number=item_number,
        status="rejected",
        reviewer=reviewer,
        notes=notes,
        group_slug=group_slug,
    )


def mark_review_queue_item(
    items: tuple[MessageReviewQueueItem, ...],
    item_number: int,
    status: ReviewStatus,
    reviewer: str,
    notes: str = "",
    group_slug: str | None = None,
) -> tuple[MessageReviewQueueItem, ...]:
    resolved_item_number = resolve_review_queue_item_number(
        items=items,
        item_number=item_number,
        group_slug=group_slug,
    )
    if resolved_item_number < 1 or resolved_item_number > len(items):
        msg = "Review queue item number is out of range"
        raise MessageReviewQueueUpdateError(msg)

    updated_items = list(items)
    original = updated_items[resolved_item_number - 1]
    updated_items[resolved_item_number - 1] = MessageReviewQueueItem(
        draft=original.draft,
        status=status,
        reviewer=_clean_reviewer(reviewer),
        notes=notes.strip(),
        routing=original.routing,
    )
    return tuple(updated_items)


def resolve_review_queue_item_number(
    *,
    items: tuple[MessageReviewQueueItem, ...],
    item_number: int,
    group_slug: str | None = None,
) -> int:
    if group_slug is None:
        return item_number
    filtered = filter_review_queue_items(items, group_slug=group_slug)
    if item_number < 1 or item_number > len(filtered):
        msg = "Review queue item number is out of range for group"
        raise MessageReviewQueueUpdateError(msg)
    target_item = filtered[item_number - 1]
    for index, item in enumerate(items, start=1):
        if item is target_item:
            return index
    msg = "Review queue item could not be resolved"
    raise MessageReviewQueueUpdateError(msg)


def message_review_queue_item_to_json(
    item: MessageReviewQueueItem,
) -> dict[str, Any]:
    return {
        "draft": message_draft_to_json(item.draft),
        "status": item.status,
        "reviewer": item.reviewer,
        "notes": item.notes,
        "routing": message_review_routing_to_json(item.routing),
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
            routing=message_review_routing_from_json(data.get("routing")),
        )
    except (KeyError, TypeError, ValueError) as error:
        msg = "Saved message review queue item is invalid"
        raise MessageReviewQueueStoreError(msg) from error


def message_review_routing_to_json(
    routing: MessageReviewRouting | None,
) -> dict[str, Any] | None:
    if routing is None:
        return None
    return {
        "group_slug": routing.group_slug,
        "group_name": routing.group_name,
        "destination_kind": routing.destination_kind,
        "destination_ref": routing.destination_ref,
        "channel_adapter": routing.channel_adapter,
        "message_tone": routing.message_tone,
        "max_messages_per_run": routing.max_messages_per_run,
        "min_interval_seconds": routing.min_interval_seconds,
    }


def message_review_routing_from_json(
    data: object,
) -> MessageReviewRouting | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        msg = "Saved message review queue routing must be an object"
        raise MessageReviewQueueStoreError(msg)

    try:
        return MessageReviewRouting(
            group_slug=str(data["group_slug"]).strip().lower(),
            group_name=str(data["group_name"]).strip(),
            destination_kind=str(data["destination_kind"]).strip().lower(),
            destination_ref=_optional_str(data.get("destination_ref")),
            channel_adapter=str(data["channel_adapter"]).strip().lower(),
            message_tone=str(data["message_tone"]).strip().lower(),
            max_messages_per_run=int(data.get("max_messages_per_run", 0)),
            min_interval_seconds=int(data.get("min_interval_seconds", 0)),
        )
    except (KeyError, TypeError, ValueError) as error:
        msg = "Saved message review queue routing is invalid"
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
