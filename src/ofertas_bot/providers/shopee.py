from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.http import HttpRequest
from ofertas_bot.providers.provider_settings import get_provider_base_urls
from ofertas_bot.providers.real_http_guard import (
    RealHttpPrerequisites,
    validate_real_http_prerequisites,
)
from ofertas_bot.providers.shopee_gateway import ShopeeGateway
from ofertas_bot.providers.shopee_mapper import ShopeeOfferMapper
from ofertas_bot.providers.shopee_signed_request import ShopeeSignedRequestBuilder
from ofertas_bot.providers.transport import UrllibHttpTransport
from ofertas_bot.settings import Settings


class ShopeeConfigurationError(RuntimeError):
    """Raised when Shopee credentials are missing or invalid."""


@dataclass(frozen=True)
class ShopeeProvider:
    settings: Settings
    marketplace: Marketplace = Marketplace.SHOPEE
    mapper: ShopeeOfferMapper = field(default_factory=ShopeeOfferMapper)
    gateway: ShopeeGateway | None = None

    def fetch(self, niche: str, limit: int) -> list[Offer]:
        self._validate_configuration()
        if self.settings.enable_real_http:
            self.validate_real_http_ready()
        gateway = self._get_gateway()
        if gateway.transport is None:
            raise NotImplementedError(
                "Shopee API integration is not implemented yet. "
                "Use an injected fake transport while credentials and endpoint "
                "mapping are prepared."
            )

        return gateway.execute_search(
            keyword=niche,
            niche=niche,
            limit=limit,
            timestamp=int(time()),
        )

    def build_search_request(self, keyword: str, limit: int, timestamp: int) -> HttpRequest:
        self._validate_configuration()
        return self._get_gateway().build_search_request(
            keyword=keyword,
            limit=limit,
            timestamp=timestamp,
        )

    def validate_real_http_ready(self) -> None:
        base_urls = get_provider_base_urls()
        validate_real_http_prerequisites(
            RealHttpPrerequisites(
                provider_name="Shopee",
                enabled=self.settings.enable_real_http,
                base_url=base_urls.shopee,
                required_config={
                    "Shopee partner id": self.settings.shopee_partner_id,
                    "Shopee tracking id": self.settings.shopee_tracking_id,
                    "Shopee API credential": self.settings.shopee_secret_key,
                },
            )
        )

    def normalize_response(
        self,
        response_data: dict[str, Any],
        niche: str,
        limit: int,
    ) -> list[Offer]:
        if self.gateway:
            return self.gateway.normalize_search_response(
                response_data=response_data,
                niche=niche,
                limit=limit,
            )

        items = response_data.get("items", [])
        if not isinstance(items, list):
            msg = "Shopee response field 'items' must be a list"
            raise ValueError(msg)

        return [self.mapper.map_item(item=item, niche=niche) for item in items[:limit]]

    def _get_gateway(self) -> ShopeeGateway:
        if self.gateway:
            return self.gateway

        builder = ShopeeSignedRequestBuilder(
            partner_id=self.settings.shopee_partner_id or "",
            api_credential=self.settings.shopee_secret_key or "",
            base_url=get_provider_base_urls().shopee,
        )
        transport = UrllibHttpTransport() if self.settings.enable_real_http else None
        return ShopeeGateway(request_builder=builder, mapper=self.mapper, transport=transport)

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
