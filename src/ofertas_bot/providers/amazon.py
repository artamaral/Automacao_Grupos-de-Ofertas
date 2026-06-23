from __future__ import annotations

from dataclasses import dataclass

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.settings import Settings


class AmazonConfigurationError(RuntimeError):
    """Raised when Amazon PA API credentials are missing or invalid."""


@dataclass(frozen=True)
class AmazonProvider:
    settings: Settings
    marketplace: Marketplace = Marketplace.AMAZON

    def fetch(self, niche: str, limit: int) -> list[Offer]:
        self._validate_configuration()
        raise NotImplementedError(
            "Amazon PA API integration is not implemented yet. "
            "Use the mock provider while credentials and endpoint mapping are prepared."
        )

    def _validate_configuration(self) -> None:
        missing = []

        if not self.settings.amazon_access_key:
            missing.append("AMAZON_ACCESS_KEY")

        if not self.settings.amazon_secret_key:
            missing.append("AMAZON_SECRET_KEY")

        if not self.settings.amazon_partner_tag:
            missing.append("AMAZON_PARTNER_TAG")

        if missing:
            names = ", ".join(missing)
            raise AmazonConfigurationError(
                f"Missing Amazon configuration: {names}. "
                "Set these values in your local .env file."
            )
