from __future__ import annotations

from dataclasses import dataclass

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.settings import Settings


class ShopeeConfigurationError(RuntimeError):
    """Raised when Shopee credentials are missing or invalid."""


@dataclass(frozen=True)
class ShopeeProvider:
    settings: Settings
    marketplace: Marketplace = Marketplace.SHOPEE

    def fetch(self, niche: str, limit: int) -> list[Offer]:
        self._validate_configuration()
        raise NotImplementedError(
            "Shopee API integration is not implemented yet. "
            "Use the mock provider while credentials and endpoint mapping are prepared."
        )

    def _validate_configuration(self) -> None:
        missing = []

        if not self.settings.shopee_partner_id:
            missing.append("SHOPEE_PARTNER_ID")

        if not self.settings.shopee_secret_key:
            missing.append("SHOPEE_SECRET_KEY")

        if missing:
            names = ", ".join(missing)
            raise ShopeeConfigurationError(
                f"Missing Shopee configuration: {names}. "
                "Set these values in your local .env file."
            )
