from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ofertas_bot.models import Marketplace, Offer


class OfferStoreError(ValueError):
    """Raised when local offer storage cannot parse saved data."""


class OfferStoreWriteError(OSError):
    """Raised when local offer storage cannot write data."""


class JsonOfferStore:
    """Optional local JSON storage for normalized offers."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, offers: list[Offer]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = [offer_to_json(offer) for offer in offers]
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            msg = f"Could not write offers JSON to {self.path}"
            raise OfferStoreWriteError(msg) from error

    def load(self) -> list[Offer]:
        if not self.path.exists():
            return []

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            msg = "Saved offers JSON is invalid"
            raise OfferStoreError(msg) from error

        if not isinstance(payload, list):
            msg = "Saved offers JSON must contain a list"
            raise OfferStoreError(msg)

        return [offer_from_json(item) for item in payload]


def offer_to_json(offer: Offer) -> dict[str, Any]:
    return {
        "marketplace": offer.marketplace.value,
        "title": offer.title,
        "url": offer.url,
        "image_url": offer.image_url,
        "price": offer.price,
        "old_price": offer.old_price,
        "commission_rate": offer.commission_rate,
        "sales_count": offer.sales_count,
        "rating": offer.rating,
        "niche": offer.niche,
        "item_id": offer.item_id,
        "is_prime_or_free_shipping": offer.is_prime_or_free_shipping,
        "shop_type_code": offer.shop_type_code,
    }


def offer_from_json(data: object) -> Offer:
    if not isinstance(data, dict):
        msg = "Saved offer item must be an object"
        raise OfferStoreError(msg)

    try:
        return Offer(
            marketplace=Marketplace(str(data["marketplace"])),
            title=str(data["title"]),
            url=str(data["url"]),
            image_url=_optional_str(data.get("image_url")),
            price=float(data["price"]),
            old_price=_optional_float(data.get("old_price")),
            commission_rate=float(data["commission_rate"]),
            sales_count=int(data["sales_count"]),
            rating=_optional_float(data.get("rating")),
            niche=str(data["niche"]),
            item_id=_optional_int(data.get("item_id")),
            is_prime_or_free_shipping=bool(data.get("is_prime_or_free_shipping", False)),
            shop_type_code=_optional_int(data.get("shop_type_code")),
        )
    except (KeyError, TypeError, ValueError) as error:
        msg = "Saved offer item is invalid"
        raise OfferStoreError(msg) from error


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)
