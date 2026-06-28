from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ofertas_bot.models import MessageDraft, Offer


class SelectionStateStoreError(ValueError):
    """Raised when local selection state storage cannot parse saved data."""


class SelectionStateStoreWriteError(OSError):
    """Raised when local selection state storage cannot write data."""


@dataclass(frozen=True)
class SelectionStateRecord:
    stable_key: str
    marketplace: str
    niche: str
    title: str
    url: str
    item_id: int | None = None
    selected_at: str | None = None
    cooldown_until: str | None = None
    last_sent_at: str | None = None
    selection_count: int = 0
    sent_count: int = 0


class JsonSelectionStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, records: dict[str, SelectionStateRecord]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = [
                selection_state_record_to_json(record)
                for record in sorted(records.values(), key=lambda item: item.stable_key)
            ]
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            msg = f"Could not write selection state JSON to {self.path}"
            raise SelectionStateStoreWriteError(msg) from error

    def load(self) -> dict[str, SelectionStateRecord]:
        if not self.path.exists():
            return {}

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            msg = "Saved selection state JSON is invalid"
            raise SelectionStateStoreError(msg) from error

        if not isinstance(payload, list):
            msg = "Saved selection state JSON must contain a list"
            raise SelectionStateStoreError(msg)

        records = [selection_state_record_from_json(item) for item in payload]
        return {record.stable_key: record for record in records}


def selection_state_record_to_json(record: SelectionStateRecord) -> dict[str, Any]:
    return {
        "stable_key": record.stable_key,
        "marketplace": record.marketplace,
        "niche": record.niche,
        "title": record.title,
        "url": record.url,
        "item_id": record.item_id,
        "selected_at": record.selected_at,
        "cooldown_until": record.cooldown_until,
        "last_sent_at": record.last_sent_at,
        "selection_count": record.selection_count,
        "sent_count": record.sent_count,
    }


def selection_state_record_from_json(data: object) -> SelectionStateRecord:
    if not isinstance(data, dict):
        msg = "Saved selection state item must be an object"
        raise SelectionStateStoreError(msg)

    try:
        return SelectionStateRecord(
            stable_key=str(data["stable_key"]),
            marketplace=str(data["marketplace"]),
            niche=str(data["niche"]),
            title=str(data["title"]),
            url=str(data["url"]),
            item_id=_optional_int(data.get("item_id")),
            selected_at=_optional_str(data.get("selected_at")),
            cooldown_until=_optional_str(data.get("cooldown_until")),
            last_sent_at=_optional_str(data.get("last_sent_at")),
            selection_count=int(data.get("selection_count", 0)),
            sent_count=int(data.get("sent_count", 0)),
        )
    except (KeyError, TypeError, ValueError) as error:
        msg = "Saved selection state item is invalid"
        raise SelectionStateStoreError(msg) from error


def merge_selection_state_into_offers(
    offers: list[Offer],
    records: dict[str, SelectionStateRecord],
) -> list[Offer]:
    merged: list[Offer] = []
    for offer in offers:
        record = records.get(offer.stable_key)
        if record is None:
            merged.append(offer)
            continue
        merged.append(
            Offer(
                marketplace=offer.marketplace,
                title=offer.title,
                url=offer.url,
                image_url=offer.image_url,
                price=offer.price,
                old_price=offer.old_price,
                commission_rate=offer.commission_rate,
                sales_count=offer.sales_count,
                rating=offer.rating,
                niche=offer.niche,
                item_id=offer.item_id,
                is_prime_or_free_shipping=offer.is_prime_or_free_shipping,
                shop_type_code=offer.shop_type_code,
                selected_at=record.selected_at,
                cooldown_until=record.cooldown_until,
                last_sent_at=record.last_sent_at,
            )
        )
    return merged


def stamp_selected_offers(
    offers: list[Offer],
    *,
    selected_at: str,
    cooldown_until: str,
) -> list[Offer]:
    return [
        Offer(
            marketplace=offer.marketplace,
            title=offer.title,
            url=offer.url,
            image_url=offer.image_url,
            price=offer.price,
            old_price=offer.old_price,
            commission_rate=offer.commission_rate,
            sales_count=offer.sales_count,
            rating=offer.rating,
            niche=offer.niche,
            item_id=offer.item_id,
            is_prime_or_free_shipping=offer.is_prime_or_free_shipping,
            shop_type_code=offer.shop_type_code,
            selected_at=selected_at,
            cooldown_until=cooldown_until,
            last_sent_at=offer.last_sent_at,
        )
        for offer in offers
    ]


def update_selection_state_from_selected_offers(
    records: dict[str, SelectionStateRecord],
    offers: list[Offer],
) -> dict[str, SelectionStateRecord]:
    updated = dict(records)
    for offer in offers:
        current = updated.get(offer.stable_key)
        updated[offer.stable_key] = _build_selection_state_record(
            offer,
            selected_at=offer.selected_at,
            cooldown_until=offer.cooldown_until,
            last_sent_at=current.last_sent_at if current is not None else offer.last_sent_at,
            selection_count=(current.selection_count + 1) if current is not None else 1,
            sent_count=current.sent_count if current is not None else 0,
        )
    return updated


def update_selection_state_last_sent_at(
    records: dict[str, SelectionStateRecord],
    *,
    drafts: tuple[MessageDraft, ...],
    last_sent_at: str,
) -> dict[str, SelectionStateRecord]:
    updated = dict(records)
    for draft in drafts:
        offer = draft.offer
        current = updated.get(offer.stable_key)
        updated[offer.stable_key] = _build_selection_state_record(
            offer,
            selected_at=(current.selected_at if current is not None else offer.selected_at),
            cooldown_until=(
                current.cooldown_until if current is not None else offer.cooldown_until
            ),
            last_sent_at=last_sent_at,
            selection_count=current.selection_count if current is not None else 0,
            sent_count=(current.sent_count + 1) if current is not None else 1,
        )
    return updated


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _build_selection_state_record(
    offer: Offer,
    *,
    selected_at: str | None,
    cooldown_until: str | None,
    last_sent_at: str | None,
    selection_count: int,
    sent_count: int,
) -> SelectionStateRecord:
    return SelectionStateRecord(
        stable_key=offer.stable_key,
        marketplace=offer.marketplace.value,
        niche=offer.niche,
        title=offer.title,
        url=offer.url,
        item_id=offer.item_id,
        selected_at=selected_at,
        cooldown_until=cooldown_until,
        last_sent_at=last_sent_at,
        selection_count=selection_count,
        sent_count=sent_count,
    )
