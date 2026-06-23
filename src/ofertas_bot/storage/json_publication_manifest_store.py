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
        )
        for draft in drafts
    )


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
        )
    except (KeyError, TypeError, ValueError) as error:
        msg = "Saved publication manifest item is invalid"
        raise PublicationManifestStoreError(msg) from error
