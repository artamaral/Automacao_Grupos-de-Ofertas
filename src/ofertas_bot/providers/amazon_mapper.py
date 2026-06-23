from __future__ import annotations

from typing import Any

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.mapper import ExternalOfferPayload, OfferMapper


class AmazonOfferMapper:
    def __init__(self) -> None:
        self._mapper = OfferMapper()

    def map_item(self, item: dict[str, Any], niche: str) -> Offer:
        listing = self._first_listing(item)
        payload = ExternalOfferPayload(
            marketplace=Marketplace.AMAZON,
            title=str(self._get_nested(item, "ItemInfo", "Title", "DisplayValue") or ""),
            url=str(item.get("DetailPageURL", "")),
            price=self._float_or_zero(self._get_nested(listing, "Price", "Amount")),
            old_price=self._optional_float(self._get_nested(listing, "SavingBasis", "Amount")),
            niche=niche,
            image_url=self._optional_str(
                self._get_nested(item, "Images", "Primary", "Medium", "URL")
            ),
        )
        return self._mapper.map_external_offer(payload)

    def _first_listing(self, item: dict[str, Any]) -> dict[str, Any]:
        listings = self._get_nested(item, "Offers", "Listings")
        if isinstance(listings, list) and listings and isinstance(listings[0], dict):
            return listings[0]
        return {}

    def _get_nested(self, value: dict[str, Any], *keys: str) -> Any:
        current: Any = value
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    def _float_or_zero(self, value: Any) -> float:
        if value is None or value == "":
            return 0.0
        return float(value)

    def _optional_float(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        return float(value)

    def _optional_str(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
