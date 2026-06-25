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
from ofertas_bot.storage.json_message_review_queue_store import (
    MessageReviewQueueItem,
)

PublicationManifestStatus = Literal["ready"]
VALID_PUBLICATION_MANIFEST_STATUSES = {"ready"}


class PublicationManifestStoreError(ValueError):
    """Raised when local publication manifest storage cannot parse saved data."""


class PublicationManifestStoreWriteError(OSError):
    """Raised when local publication manifest storage cannot write data."""


@dataclass(frozen=True)
class PublicationManifestItem:
    draft: MessageDraft
    target: str
    status: PublicationManifestStatus
    created_at: str
    channel_adapter: str = "whatsapp"
    max_messages_per_run: int = 0
    max_messages_per_hour: int = 0
    min_interval_seconds: int = 0
    quiet_periods: tuple[str, ...] = ()


class JsonPublicationManifestStore:
    """Optional local JSON storage for future controlled publication manifests."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, items: tuple[PublicationManifestItem, ...]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = [publication_manifest_item_to_json(item) for item in items]
            self.path.write_text(
                json.dumps(payload, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            msg = f"Could not write publication manifest JSON to {self.path}"
            raise PublicationManifestStoreWriteError(msg) from error

    def load(self) -> tuple[PublicationManifestItem, ...]:
        if not self.path.exists():
            return ()

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            msg = "Saved publication manifest JSON is invalid"
            raise PublicationManifestStoreError(msg) from error

        if not isinstance(payload, list):
            msg = "Saved publication manifest JSON must contain a list"
            raise PublicationManifestStoreError(msg)

        return tuple(publication_manifest_item_from_json(item) for item in payload)


def create_publication_manifest(
    drafts: tuple[MessageDraft, ...],
    target: str,
    created_at: str,
    channel_adapter: str = "whatsapp",
) -> tuple[PublicationManifestItem, ...]:
    clean_target = target.strip()
    if not clean_target:
        msg = "Publication manifest target is required"
        raise PublicationManifestStoreError(msg)

    return tuple(
        PublicationManifestItem(
            draft=draft,
            target=clean_target,
            status="ready",
            created_at=created_at,
            channel_adapter=channel_adapter.strip().lower(),
            max_messages_per_run=0,
            max_messages_per_hour=0,
            min_interval_seconds=0,
            quiet_periods=(),
        )
        for draft in drafts
    )


def create_publication_manifest_from_review_queue(
    items: tuple[MessageReviewQueueItem, ...],
    created_at: str,
    fallback_target: str | None = None,
    fallback_channel_adapter: str = "whatsapp",
) -> tuple[PublicationManifestItem, ...]:
    clean_fallback_target = _clean_optional_target(fallback_target)
    clean_fallback_channel_adapter = fallback_channel_adapter.strip().lower()
    manifest: list[PublicationManifestItem] = []

    for item in items:
        if item.status != "approved":
            continue
        target = _resolve_review_queue_target(
            item=item,
            fallback_target=clean_fallback_target,
        )
        channel_adapter = _resolve_review_queue_channel_adapter(
            item=item,
            fallback_channel_adapter=clean_fallback_channel_adapter,
        )
        max_messages_per_run = _resolve_review_queue_max_messages_per_run(item=item)
        max_messages_per_hour = _resolve_review_queue_max_messages_per_hour(item=item)
        min_interval_seconds = _resolve_review_queue_min_interval_seconds(item=item)
        quiet_periods = _resolve_review_queue_quiet_periods(item=item)
        manifest.append(
            PublicationManifestItem(
                draft=item.draft,
                target=target,
                status="ready",
                created_at=created_at,
                channel_adapter=channel_adapter,
                max_messages_per_run=max_messages_per_run,
                max_messages_per_hour=max_messages_per_hour,
                min_interval_seconds=min_interval_seconds,
                quiet_periods=quiet_periods,
            )
        )

    return tuple(manifest)


def validate_publication_manifest(
    items: tuple[PublicationManifestItem, ...],
) -> tuple[str, ...]:
    issues: list[str] = []

    if not items:
        issues.append("manifesto vazio")

    for index, item in enumerate(items, start=1):
        if item.status != "ready":
            issues.append(f"item {index} com status inválido")
        if not item.target.strip():
            issues.append(f"item {index} sem alvo")
        if not item.created_at.strip():
            issues.append(f"item {index} sem data de criação")
        if not item.channel_adapter.strip():
            issues.append(f"item {index} sem canal")
        if item.max_messages_per_run < 0:
            issues.append(f"item {index} com limite de mensagens invalido")
        if item.max_messages_per_hour < 0:
            issues.append(f"item {index} com limite por hora invalido")
        if item.min_interval_seconds < 0:
            issues.append(f"item {index} com intervalo invalido")
        if not item.draft.text.strip():
            issues.append(f"item {index} sem mensagem")
        if not item.draft.offer.url.strip():
            issues.append(f"item {index} sem link da oferta")

    return tuple(issues)


def publication_manifest_item_to_json(
    item: PublicationManifestItem,
) -> dict[str, Any]:
    return {
        "draft": message_draft_to_json(item.draft),
        "target": item.target,
        "status": item.status,
        "created_at": item.created_at,
        "channel_adapter": item.channel_adapter,
        "max_messages_per_run": item.max_messages_per_run,
        "max_messages_per_hour": item.max_messages_per_hour,
        "min_interval_seconds": item.min_interval_seconds,
        "quiet_periods": list(item.quiet_periods),
    }


def publication_manifest_item_from_json(data: object) -> PublicationManifestItem:
    if not isinstance(data, dict):
        msg = "Saved publication manifest item must be an object"
        raise PublicationManifestStoreError(msg)

    try:
        raw_status = str(data["status"])
        if raw_status not in VALID_PUBLICATION_MANIFEST_STATUSES:
            msg = "Saved publication manifest status is invalid"
            raise PublicationManifestStoreError(msg)
        status = cast(PublicationManifestStatus, raw_status)
        return PublicationManifestItem(
            draft=message_draft_from_json(data["draft"]),
            target=str(data["target"]),
            status=status,
            created_at=str(data["created_at"]),
            channel_adapter=str(data.get("channel_adapter", "whatsapp")).strip().lower(),
            max_messages_per_run=int(data.get("max_messages_per_run", 0)),
            max_messages_per_hour=int(data.get("max_messages_per_hour", 0)),
            min_interval_seconds=int(data.get("min_interval_seconds", 0)),
            quiet_periods=tuple(str(item) for item in data.get("quiet_periods", ())),
        )
    except (KeyError, TypeError, ValueError) as error:
        msg = "Saved publication manifest item is invalid"
        raise PublicationManifestStoreError(msg) from error


def _clean_optional_target(target: str | None) -> str | None:
    if target is None:
        return None
    clean_target = target.strip()
    if not clean_target:
        return None
    return clean_target


def _resolve_review_queue_target(
    *,
    item: MessageReviewQueueItem,
    fallback_target: str | None,
) -> str:
    if item.routing is not None and item.routing.destination_ref:
        return item.routing.destination_ref
    if fallback_target is not None:
        return fallback_target
    msg = "Publication manifest target is required for approved review queue items"
    raise PublicationManifestStoreError(msg)


def _resolve_review_queue_channel_adapter(
    *,
    item: MessageReviewQueueItem,
    fallback_channel_adapter: str,
) -> str:
    if item.routing is not None and item.routing.channel_adapter:
        return item.routing.channel_adapter
    if fallback_channel_adapter:
        return fallback_channel_adapter
    msg = "Publication manifest channel adapter is required for approved review queue items"
    raise PublicationManifestStoreError(msg)


def _resolve_review_queue_max_messages_per_run(
    *,
    item: MessageReviewQueueItem,
) -> int:
    if item.routing is None:
        return 0
    return item.routing.max_messages_per_run


def _resolve_review_queue_min_interval_seconds(
    *,
    item: MessageReviewQueueItem,
) -> int:
    if item.routing is None:
        return 0
    return item.routing.min_interval_seconds


def _resolve_review_queue_max_messages_per_hour(
    *,
    item: MessageReviewQueueItem,
) -> int:
    if item.routing is None:
        return 0
    return item.routing.max_messages_per_hour


def _resolve_review_queue_quiet_periods(
    *,
    item: MessageReviewQueueItem,
) -> tuple[str, ...]:
    if item.routing is None:
        return ()
    return item.routing.quiet_periods
