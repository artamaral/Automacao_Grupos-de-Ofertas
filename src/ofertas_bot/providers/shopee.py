from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.http import HttpRequest
from ofertas_bot.providers.provider_settings import get_provider_graphql_urls
from ofertas_bot.providers.real_http_guard import (
    RealHttpPrerequisites,
    RealHttpValidationError,
    validate_real_http_prerequisites,
)
from ofertas_bot.providers.shopee_gateway import ShopeeGateway
from ofertas_bot.providers.shopee_graphql import (
    SHOPEE_SORT_LATEST_DESC,
    ShopeeGraphqlGateway,
    ShopeeGraphqlOfferMapper,
    ShopeeGraphqlSigner,
    ShopeeOfferListGraphqlRequestBuilder,
    ShopeeShortLinkGraphqlRequestBuilder,
)
from ofertas_bot.providers.shopee_mapper import ShopeeOfferMapper
from ofertas_bot.providers.transport import UrllibHttpTransport
from ofertas_bot.settings import Settings

MAX_SHOPEE_PARTNER_ID = 4_294_967_295


class ShopeeConfigurationError(RuntimeError):
    """Raised when Shopee credentials are missing or invalid."""


@dataclass(frozen=True)
class ShopeeProvider:
    settings: Settings
    marketplace: Marketplace = Marketplace.SHOPEE
    mapper: ShopeeOfferMapper = field(default_factory=ShopeeOfferMapper)
    gateway: ShopeeGateway | None = None
    graphql_gateway: ShopeeGraphqlGateway | None = None

    def fetch(self, niche: str, limit: int) -> list[Offer]:
        self._validate_configuration()
        if self.settings.enable_real_http:
            self.validate_real_http_ready()
        gateway = self._get_graphql_gateway()
        if gateway.transport is None:
            raise NotImplementedError(
                "Shopee GraphQL transport is not configured. "
                "Use an injected fake transport or enable real HTTP after approval."
            )

        return gateway.execute_offer_list(
            keyword=niche,
            niche=niche,
            limit=limit,
            timestamp=int(time()),
            sort_type=SHOPEE_SORT_LATEST_DESC,
        )

    def fetch_raw_response(self, niche: str, limit: int) -> dict[str, Any]:
        self._validate_configuration()
        if self.settings.enable_real_http:
            self.validate_real_http_ready()
        gateway = self._get_graphql_gateway()
        if gateway.transport is None:
            raise NotImplementedError(
                "Shopee GraphQL transport is not configured. "
                "Use an injected fake transport or enable real HTTP after approval."
            )

        return gateway.execute_raw_offer_list(
            keyword=niche,
            limit=limit,
            timestamp=int(time()),
        )

    def build_search_request(self, keyword: str, limit: int, timestamp: int) -> HttpRequest:
        self._validate_configuration()
        return self._get_graphql_gateway().build_offer_list_request(
            keyword=keyword,
            limit=limit,
            timestamp=timestamp,
        )

    def validate_real_http_ready(self) -> None:
        graphql_urls = get_provider_graphql_urls()
        validate_real_http_prerequisites(
            RealHttpPrerequisites(
                provider_name="Shopee",
                enabled=self.settings.enable_real_http,
                base_url=graphql_urls.shopee,
                required_config={
                    "Shopee app id": self.settings.shopee_partner_id,
                    "Shopee tracking id": self.settings.shopee_tracking_id,
                    "Shopee API credential": self.settings.shopee_secret_key,
                },
            )
        )
        self._validate_partner_id_range()

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

        return self._get_graphql_gateway().normalize_offer_list_response(
            response_data=response_data,
            niche=niche,
            limit=limit,
        )

    def _get_gateway(self) -> ShopeeGateway:
        if not self.gateway:
            msg = "Shopee REST gateway is legacy and is not configured by default"
            raise NotImplementedError(msg)
        return self.gateway

    def _get_graphql_gateway(self) -> ShopeeGraphqlGateway:
        if self.graphql_gateway:
            return self.graphql_gateway

        signer = ShopeeGraphqlSigner(
            credential=self.settings.shopee_partner_id or "",
            api_secret=self.settings.shopee_secret_key or "",
        )
        graphql_url = get_provider_graphql_urls().shopee
        offer_list_builder = ShopeeOfferListGraphqlRequestBuilder(
            signer=signer,
            graphql_url=graphql_url,
        )
        short_link_builder = ShopeeShortLinkGraphqlRequestBuilder(
            signer=signer,
            graphql_url=graphql_url,
        )
        transport = UrllibHttpTransport() if self.settings.enable_real_http else None
        return ShopeeGraphqlGateway(
            offer_list_builder=offer_list_builder,
            short_link_builder=short_link_builder,
            mapper=ShopeeGraphqlOfferMapper(marketplace=Marketplace.SHOPEE),
            transport=transport,
        )

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

    def _validate_partner_id_range(self) -> None:
        partner_id = self.settings.shopee_partner_id or ""
        if not partner_id.isdecimal():
            msg = "Real HTTP for Shopee is blocked: Shopee partner id must be numeric"
            raise RealHttpValidationError(msg)

        numeric_partner_id = int(partner_id)
        if numeric_partner_id > MAX_SHOPEE_PARTNER_ID:
            msg = "Real HTTP for Shopee is blocked: Shopee partner id is out of range"
            raise RealHttpValidationError(msg)
