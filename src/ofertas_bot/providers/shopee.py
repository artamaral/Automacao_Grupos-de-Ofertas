from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.shopee_mapper import ShopeeOfferMapper
from ofertas_bot.settings import Settings


class ShopeeConfigurationError(RuntimeError):
    """Raised when Shopee credentials are missing or invalid."""


@dataclass(frozen=True)
class ShopeeProvider:
    settings: Settings
    marketplace: Marketplace = Marketplace.SHOPEE
    mapper: ShopeeOfferMapper = field(default_factory=ShopeeOfferMapper)

    def fetch(self, niche: str, limit: int) -> list[Offer]:
        self._validate_configuration()
        raise NotImplementedError(
            "Shopee API integration is not implemented yet. "
            "Use the mock provider while credentials and endpoint mapping are prepared."
        )

    def normalize_response(
        self,
        response_data: dict[str, Any],
        niche: str,
        limit: int,
    ) -> list[Offer]:
        items = response_data.get("items", [])
        if not isinstance(items, list):
            msg = "Shopee response field 'items' must be a list"
            raise ValueError(msg)

        return [self.mapper.map_item(item=item, niche=niche) for item in items[:limit]]

    def _validate_configuration(self) -> None:
        missing = []

        if not self.settings.shopee_partner_id:
            missing.append("SHOPEE_PARTNER_ID")

        if not self.settings.shopee_secret_key:
            missing.append("SHOPEE_" "SECRET_KEY")

        if missing:
            names = ", ".join(missing)
            raise ShopeeConfigurationError(
                f"Missing Shopee configuration: {names}. "
                "Set these values in your local .env file."
            )
