from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.gateway import execute_provider_request
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
    SHOPEE_PRODUCT_OFFER_LIST_OPERATION,
    ShopeeGraphqlGateway,
    ShopeeGraphqlOfferMapper,
    ShopeeGraphqlSigner,
    ShopeeOfferListGraphqlRequestBuilder,
    ShopeeShortLinkGraphqlRequestBuilder,
    build_graphql_request,
    build_product_offer_query,
    load_shopee_offer_list_query,
)
from ofertas_bot.providers.shopee_mapper import ShopeeOfferMapper
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

    def fetch_offer_search_raw_response(self, offer_name: str, limit: int) -> dict[str, Any]:
        self._validate_configuration()
        if self.settings.enable_real_http:
            self.validate_real_http_ready()

        return self._execute_graphql_query(
            query=self._build_shopee_offer_search_query(),
            operation_name="ShopeeOfferList",
            variables={
                "keyword": offer_name,
                "sortType": SHOPEE_SORT_LATEST_DESC,
                "page": 1,
                "limit": limit,
            },
        )

    def fetch_product_match_raw_response(self, match_id: int, limit: int) -> dict[str, Any]:
        self._validate_configuration()
        if self.settings.enable_real_http:
            self.validate_real_http_ready()

        return self._execute_graphql_query(
            query=build_product_offer_query(
                list_type=4,
                match_id=match_id,
                page=1,
                limit=limit,
            ),
            operation_name=SHOPEE_PRODUCT_OFFER_LIST_OPERATION,
            variables={},
        )

    def normalize_custom_response(
        self,
        *,
        response_data: dict[str, Any],
        niche: str,
        limit: int,
        root_field: str,
    ) -> list[Offer]:
        gateway = self._get_graphql_gateway()
        if root_field == gateway.offer_list_root_field:
            return gateway.normalize_offer_list_response(
                response_data=response_data,
                niche=niche,
                limit=limit,
            )

        custom_gateway = ShopeeGraphqlGateway(
            offer_list_builder=gateway.offer_list_builder,
            short_link_builder=gateway.short_link_builder,
            mapper=ShopeeGraphqlOfferMapper(marketplace=Marketplace.SHOPEE),
            offer_list_root_field=root_field,
            transport=gateway.transport,
            retry_policy=gateway.retry_policy,
            sleeper=gateway.sleeper,
        )
        return custom_gateway.normalize_offer_list_response(
            response_data=response_data,
            niche=niche,
            limit=limit,
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
        offer_list_query = load_shopee_offer_list_query(self.settings.shopee_offer_list_query_file)
        offer_list_builder = ShopeeOfferListGraphqlRequestBuilder(
            signer=signer,
            graphql_url=graphql_url,
            query=offer_list_query,
            operation_name=self.settings.shopee_offer_list_operation,
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
            offer_list_root_field=self.settings.shopee_offer_list_root_field,
            transport=transport,
        )

    def _execute_graphql_query(
        self,
        *,
        query: str,
        operation_name: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        gateway = self._get_graphql_gateway()
        if gateway.transport is None:
            raise NotImplementedError(
                "Shopee GraphQL transport is not configured. "
                "Use an injected fake transport or enable real HTTP after approval."
            )

        request = build_graphql_request(
            graphql_url=gateway.offer_list_builder.graphql_url,
            signer=gateway.offer_list_builder.signer,
            timestamp=int(time()),
            query=query,
            operation_name=operation_name,
            variables=variables,
        )
        return execute_provider_request(
            request=request,
            transport=gateway.transport,
            http_client=gateway.http_client,
            provider_name="Shopee",
            retry_policy=gateway.retry_policy,
            sleeper=gateway.sleeper,
        )

    def _build_shopee_offer_search_query(self) -> str:
        return """
query ShopeeOfferList($keyword: String, $sortType: Int, $page: Int, $limit: Int) {
  shopeeOfferV2(keyword: $keyword, sortType: $sortType, page: $page, limit: $limit) {
    nodes {
      commissionRate
      imageUrl
      offerLink
      originalLink
      offerName
      offerType
      categoryId
      collectionId
      periodStartTime
      periodEndTime
    }
    pageInfo {
      page
      limit
      hasNextPage
    }
  }
}
""".strip()

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
