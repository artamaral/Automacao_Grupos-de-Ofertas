from __future__ import annotations

from dataclasses import dataclass

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.amazon_gateway import AmazonGateway
from ofertas_bot.providers.amazon_request import AmazonSearchRequestBuilder
from ofertas_bot.providers.provider_settings import get_provider_base_urls
from ofertas_bot.settings import Settings


class AmazonConfigurationError(RuntimeError):
    """Raised when Amazon PA API credentials are missing or invalid."""


@dataclass(frozen=True)
class AmazonProvider:
    settings: Settings
    marketplace: Marketplace = Marketplace.AMAZON
    gateway: AmazonGateway | None = None

    def fetch(self, niche: str, limit: int) -> list[Offer]:
        self._validate_configuration()
        gateway = self._get_gateway()
        if gateway.transport is None:
            raise NotImplementedError(
                "Amazon PA API integration is not implemented yet. "
                "Use an injected fake transport while credentials and endpoint "
                "mapping are prepared."
            )

        return gateway.execute_search(keyword=niche, niche=niche, limit=limit)

    def _get_gateway(self) -> AmazonGateway:
        if self.gateway:
            return self.gateway

        builder = AmazonSearchRequestBuilder(
            partner_tag=self.settings.amazon_partner_tag or "",
            base_url=get_provider_base_urls().amazon,
        )
        return AmazonGateway(request_builder=builder)

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
