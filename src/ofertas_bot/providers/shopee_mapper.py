from __future__ import annotations

from typing import Any

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.mapper import ExternalOfferPayload, OfferMapper


class ShopeeOfferMapper:
    def __init__(self) -> None:
        self._mapper = OfferMapper()

    def map_item(self, item: dict[str, Any], niche: str) -> Offer:
        payload = ExternalOfferPayload(
            marketplace=Marketplace.SHOPEE,
            title=str(item.get("title", "")),
            url=str(item.get("url", "")),
            price=float(item.get("price") or 0),
            old_price=self._optional_float(item.get("old_price")),
            niche=niche,
            image_url=self._optional_str(item.get("image_url")),
            commission_rate=float(item.get("commission_rate") or 0),
            sales_count=int(item.get("sales_count") or 0),
            rating=self._optional_float(item.get("rating")),
            is_prime_or_free_shipping=bool(item.get("is_free_shipping", False)),
        )
        return self._mapper.map_external_offer(payload)

    def _optional_float(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        return float(value)

    def _optional_str(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
