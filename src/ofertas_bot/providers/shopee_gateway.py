from dataclasses import dataclass, field
from typing import Any, Protocol

from ofertas_bot.models import Offer
from ofertas_bot.providers.gateway import execute_provider_request, validate_positive_limit
from ofertas_bot.providers.http import HttpRequest, ProviderHttpClient
from ofertas_bot.providers.retry import RetryPolicy, Sleeper
from ofertas_bot.providers.shopee_mapper import ShopeeOfferMapper
from ofertas_bot.providers.transport import HttpTransport


class ShopeePayloadError(ValueError):
    """Raised when Shopee returns an unexpected payload shape."""


class ShopeeRequestBuilder(Protocol):
    def build(self, keyword: str, limit: int, timestamp: int) -> HttpRequest:
        """Build a signed Shopee search request."""


@dataclass(frozen=True)
class ShopeeGateway:
    request_builder: ShopeeRequestBuilder
    mapper: ShopeeOfferMapper = field(default_factory=ShopeeOfferMapper)
    http_client: ProviderHttpClient = field(default_factory=ProviderHttpClient)
    transport: HttpTransport | None = None
    retry_policy: RetryPolicy | None = None
    sleeper: Sleeper | None = None

    def build_search_request(
        self,
        keyword: str,
        limit: int,
        timestamp: int,
    ) -> HttpRequest:
        validate_positive_limit(limit)
        return self.request_builder.build(
            keyword=keyword,
            limit=limit,
            timestamp=timestamp,
        )

    def execute_raw_search(
        self,
        keyword: str,
        limit: int,
        timestamp: int,
    ) -> dict[str, Any]:
        request = self.build_search_request(
            keyword=keyword,
            limit=limit,
            timestamp=timestamp,
        )
        return execute_provider_request(
            request=request,
            transport=self.transport,
            http_client=self.http_client,
            provider_name="Shopee",
            retry_policy=self.retry_policy,
            sleeper=self.sleeper,
        )

    def execute_search(
        self,
        keyword: str,
        niche: str,
        limit: int,
        timestamp: int,
    ) -> list[Offer]:
        response_data = self.execute_raw_search(
            keyword=keyword,
            limit=limit,
            timestamp=timestamp,
        )
        return self.normalize_search_response(
            response_data=response_data,
            niche=niche,
            limit=limit,
        )

    def execute_paginated_search(
        self,
        keyword: str,
        niche: str,
        limit: int,
        page_size: int,
        timestamp: int,
        max_pages: int = 3,
    ) -> list[Offer]:
        validate_positive_limit(limit)
        validate_positive_limit(page_size)
        validate_positive_limit(max_pages)

        offers: list[Offer] = []
        page = 1
        while len(offers) < limit and page <= max_pages:
            request_limit = min(page_size, limit - len(offers))
            request = self._build_paginated_request(
                keyword=keyword,
                limit=request_limit,
                timestamp=timestamp,
                page=page,
            )
            response_data = execute_provider_request(
                request=request,
                transport=self.transport,
                http_client=self.http_client,
                provider_name="Shopee",
                retry_policy=self.retry_policy,
                sleeper=self.sleeper,
            )
            page_offers = self.normalize_search_response(
                response_data=response_data,
                niche=niche,
                limit=request_limit,
            )
            offers.extend(page_offers)
            if not page_offers or not self._has_next_page(response_data):
                break
            page += 1

        return offers[:limit]

    def normalize_search_response(
        self,
        response_data: dict[str, object],
        niche: str,
        limit: int,
    ) -> list[Offer]:
        validate_positive_limit(limit)
        items = response_data.get("items", [])
        if not isinstance(items, list):
            msg = "Shopee response field 'items' must be a list"
            raise ShopeePayloadError(msg)

        return [self.mapper.map_item(item=item, niche=niche) for item in items[:limit]]

    def _build_paginated_request(
        self,
        keyword: str,
        limit: int,
        timestamp: int,
        page: int,
    ) -> HttpRequest:
        request = self.build_search_request(keyword=keyword, limit=limit, timestamp=timestamp)
        return HttpRequest(
            method=request.method,
            url=request.url,
            params={**request.params, "page": page},
            headers=request.headers,
            body=request.body,
        )

    def _has_next_page(self, response_data: dict[str, object]) -> bool:
        return response_data.get("has_next_page") is True
