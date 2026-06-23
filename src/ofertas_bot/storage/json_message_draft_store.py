from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ofertas_bot.models import MessageDraft
from ofertas_bot.storage.json_offer_store import offer_from_json, offer_to_json


class MessageDraftStoreError(ValueError):
    """Raised when local message draft storage cannot parse saved data."""


class MessageDraftStoreWriteError(OSError):
    """Raised when local message draft storage cannot write data."""


class JsonMessageDraftStore:
    """Optional local JSON storage for generated message drafts."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, drafts: tuple[MessageDraft, ...]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = [message_draft_to_json(draft) for draft in drafts]
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            msg = f"Could not write message drafts JSON to {self.path}"
            raise MessageDraftStoreWriteError(msg) from error

    def load(self) -> tuple[MessageDraft, ...]:
        if not self.path.exists():
            return ()

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            msg = "Saved message drafts JSON is invalid"
            raise MessageDraftStoreError(msg) from error

        if not isinstance(payload, list):
            msg = "Saved message drafts JSON must contain a list"
            raise MessageDraftStoreError(msg)

        return tuple(message_draft_from_json(item) for item in payload)


def message_draft_to_json(draft: MessageDraft) -> dict[str, Any]:
    return {
        "offer": offer_to_json(draft.offer),
        "text": draft.text,
    }


def message_draft_from_json(data: object) -> MessageDraft:
    if not isinstance(data, dict):
        msg = "Saved message draft item must be an object"
        raise MessageDraftStoreError(msg)

    try:
        return MessageDraft(
            offer=offer_from_json(data["offer"]),
            text=str(data["text"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        msg = "Saved message draft item is invalid"
        raise MessageDraftStoreError(msg) from error
