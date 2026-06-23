from __future__ import annotations

from dataclasses import dataclass

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.amazon_gateway import AmazonGateway
from ofertas_bot.providers.amazon_request import AmazonSearchRequestBuilder
from ofertas_bot.providers.provider_settings import get_provider_base_urls
from ofertas_bot.providers.real_http_guard import (
    RealHttpPrerequisites,
    validate_real_http_prerequisites,
)
from ofertas_bot.providers.transport import UrllibHttpTransport
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
        if self.settings.enable_real_http:
            self.validate_real_http_ready()
        gateway = self._get_gateway()
        if gateway.transport is None:
            raise NotImplementedError(
                "Amazon PA API integration is not implemented yet. "
                "Use an injected fake transport while credentials and endpoint "
                "mapping are prepared."
            )

        return gateway.execute_search(keyword=niche, niche=niche, limit=limit)

    def validate_real_http_ready(self) -> None:
        base_urls = get_provider_base_urls()
        validate_real_http_prerequisites(
            RealHttpPrerequisites(
                provider_name="Amazon",
                enabled=self.settings.enable_real_http,
                base_url=base_urls.amazon,
                required_config={
                    "Amazon access key": self.settings.amazon_access_key,
                    "Amazon API credential": self.settings.amazon_secret_key,
                    "Amazon partner tag": self.settings.amazon_partner_tag,
                },
            )
        )

    def _get_gateway(self) -> AmazonGateway:
        if self.gateway:
            return self.gateway

        builder = AmazonSearchRequestBuilder(
            partner_tag=self.settings.amazon_partner_tag or "",
            base_url=get_provider_base_urls().amazon,
        )
        transport = UrllibHttpTransport() if self.settings.enable_real_http else None
        return AmazonGateway(request_builder=builder, transport=transport)

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
