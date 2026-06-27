from __future__ import annotations

from dataclasses import dataclass

from ofertas_bot.models import Marketplace, Offer


class OfferMappingError(ValueError):
    """Raised when a provider payload cannot be normalized into an Offer."""


@dataclass(frozen=True)
class ExternalOfferPayload:
    marketplace: Marketplace
    title: str
    url: str
    price: float
    old_price: float | None
    niche: str
    image_url: str | None = None
    commission_rate: float = 0.0
    sales_count: int = 0
    rating: float | None = None
    item_id: int | None = None
    is_prime_or_free_shipping: bool = False
    shop_type_code: int | None = None
    allow_unknown_price: bool = False


class OfferMapper:
    def map_external_offer(self, payload: ExternalOfferPayload) -> Offer:
        self._validate(payload)
        return Offer(
            marketplace=payload.marketplace,
            title=payload.title.strip(),
            url=payload.url.strip(),
            image_url=payload.image_url,
            price=payload.price,
            old_price=payload.old_price,
            commission_rate=payload.commission_rate,
            sales_count=payload.sales_count,
            rating=payload.rating,
            niche=payload.niche.strip(),
            item_id=payload.item_id,
            is_prime_or_free_shipping=payload.is_prime_or_free_shipping,
            shop_type_code=payload.shop_type_code,
        )

    def _validate(self, payload: ExternalOfferPayload) -> None:
        errors = []

        if not payload.title.strip():
            errors.append("title")

        if not payload.url.strip():
            errors.append("url")

        if payload.price < 0 or (payload.price == 0 and not payload.allow_unknown_price):
            errors.append("price")

        if payload.old_price is not None and payload.old_price <= 0:
            errors.append("old_price")

        if payload.commission_rate < 0:
            errors.append("commission_rate")

        if payload.sales_count < 0:
            errors.append("sales_count")

        if payload.rating is not None and not 0 <= payload.rating <= 5:
            errors.append("rating")

        if payload.item_id is not None and payload.item_id < 0:
            errors.append("item_id")

        if payload.shop_type_code is not None and payload.shop_type_code < 0:
            errors.append("shop_type_code")

        if not payload.niche.strip():
            errors.append("niche")

        if errors:
            fields = ", ".join(errors)
            raise OfferMappingError(f"Invalid external offer payload fields: {fields}")
