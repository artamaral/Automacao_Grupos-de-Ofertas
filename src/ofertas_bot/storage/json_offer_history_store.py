from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ofertas_bot.models import Marketplace, Offer


class OfferHistoryStoreError(ValueError):
    """Raised when local offer history cannot be parsed."""


class OfferHistoryStoreWriteError(OSError):
    """Raised when local offer history cannot be written."""


@dataclass(frozen=True)
class OfferHistoryEntry:
    offer_key: str
    marketplace: Marketplace
    title: str
    url: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_published_at: datetime | None = None
    publish_count: int = 0
    niches: tuple[str, ...] = ()
    group_slugs: tuple[str, ...] = ()


class JsonOfferHistoryStore:
    """Optional local JSON storage for offer traceability."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, history: dict[str, OfferHistoryEntry]) -> None:
        payload = {
            key: offer_history_entry_to_json(entry)
            for key, entry in sorted(history.items())
            if key.strip()
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            msg = f"Could not write offer history JSON to {self.path}"
            raise OfferHistoryStoreWriteError(msg) from error

    def load(self) -> dict[str, OfferHistoryEntry]:
        if not self.path.exists():
            return {}

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            msg = "Saved offer history JSON is invalid"
            raise OfferHistoryStoreError(msg) from error

        if not isinstance(payload, dict):
            msg = "Saved offer history JSON must contain an object"
            raise OfferHistoryStoreError(msg)

        return {
            str(key).strip(): offer_history_entry_from_json(item)
            for key, item in payload.items()
            if str(key).strip()
        }

    def touch_offers(
        self,
        *,
        offers: list[Offer],
        seen_at: datetime,
    ) -> dict[str, OfferHistoryEntry]:
        history = self.load()
        for offer in offers:
            current = history.get(offer.stable_key)
            if current is None:
                history[offer.stable_key] = OfferHistoryEntry(
                    offer_key=offer.stable_key,
                    marketplace=offer.marketplace,
                    title=offer.title,
                    url=offer.url,
                    first_seen_at=seen_at,
                    last_seen_at=seen_at,
                    niches=(offer.niche,),
                )
                continue

            history[offer.stable_key] = OfferHistoryEntry(
                offer_key=current.offer_key,
                marketplace=current.marketplace,
                title=offer.title,
                url=offer.url,
                first_seen_at=current.first_seen_at,
                last_seen_at=seen_at,
                last_published_at=current.last_published_at,
                publish_count=current.publish_count,
                niches=_merge_unique_values(current.niches, offer.niche),
                group_slugs=current.group_slugs,
            )

        self.save(history)
        return history

    def mark_offer_published(
        self,
        *,
        offer: Offer,
        published_at: datetime,
        group_slug: str | None = None,
    ) -> OfferHistoryEntry:
        history = self.load()
        current = history.get(offer.stable_key)
        if current is None:
            current = OfferHistoryEntry(
                offer_key=offer.stable_key,
                marketplace=offer.marketplace,
                title=offer.title,
                url=offer.url,
                first_seen_at=published_at,
                last_seen_at=published_at,
                niches=(offer.niche,),
            )

        updated = OfferHistoryEntry(
            offer_key=current.offer_key,
            marketplace=current.marketplace,
            title=offer.title,
            url=offer.url,
            first_seen_at=current.first_seen_at,
            last_seen_at=max(current.last_seen_at, published_at),
            last_published_at=published_at,
            publish_count=current.publish_count + 1,
            niches=_merge_unique_values(current.niches, offer.niche),
            group_slugs=_merge_unique_values(current.group_slugs, group_slug),
        )
        history[offer.stable_key] = updated
        self.save(history)
        return updated


def offer_history_entry_to_json(entry: OfferHistoryEntry) -> dict[str, Any]:
    return {
        "offer_key": entry.offer_key,
        "marketplace": entry.marketplace.value,
        "title": entry.title,
        "url": entry.url,
        "first_seen_at": entry.first_seen_at.isoformat(),
        "last_seen_at": entry.last_seen_at.isoformat(),
        "last_published_at": entry.last_published_at.isoformat()
        if entry.last_published_at is not None
        else None,
        "publish_count": entry.publish_count,
        "niches": list(entry.niches),
        "group_slugs": list(entry.group_slugs),
    }


def offer_history_entry_from_json(data: object) -> OfferHistoryEntry:
    if not isinstance(data, dict):
        msg = "Saved offer history entry must be an object"
        raise OfferHistoryStoreError(msg)

    try:
        return OfferHistoryEntry(
            offer_key=str(data["offer_key"]),
            marketplace=Marketplace(str(data["marketplace"])),
            title=str(data["title"]),
            url=str(data["url"]),
            first_seen_at=_parse_datetime(data["first_seen_at"]),
            last_seen_at=_parse_datetime(data["last_seen_at"]),
            last_published_at=_parse_optional_datetime(data.get("last_published_at")),
            publish_count=int(data.get("publish_count", 0)),
            niches=_parse_string_tuple(data.get("niches", [])),
            group_slugs=_parse_string_tuple(data.get("group_slugs", [])),
        )
    except (KeyError, TypeError, ValueError) as error:
        msg = "Saved offer history entry is invalid"
        raise OfferHistoryStoreError(msg) from error


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        msg = "Saved offer history datetime must be an ISO string"
        raise OfferHistoryStoreError(msg)
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        msg = "Saved offer history datetime is invalid"
        raise OfferHistoryStoreError(msg) from error


def _parse_optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    return _parse_datetime(value)


def _parse_string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        msg = "Saved offer history list fields must contain a list"
        raise OfferHistoryStoreError(msg)
    return tuple(str(item).strip() for item in value if str(item).strip())


def _merge_unique_values(values: tuple[str, ...], new_value: str | None) -> tuple[str, ...]:
    merged = list(values)
    normalized = str(new_value).strip() if new_value is not None else ""
    if normalized and normalized not in merged:
        merged.append(normalized)
    return tuple(merged)
