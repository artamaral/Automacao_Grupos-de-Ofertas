from dataclasses import dataclass, field
from typing import Any, Protocol

from ofertas_bot.models import Offer
from ofertas_bot.providers.amazon_mapper import AmazonOfferMapper
from ofertas_bot.providers.gateway import execute_provider_request, validate_positive_limit
from ofertas_bot.providers.http import HttpRequest, ProviderHttpClient
from ofertas_bot.providers.retry import RetryPolicy, Sleeper
from ofertas_bot.providers.transport import HttpTransport


class AmazonPayloadError(ValueError):
    """Raised when Amazon returns an unexpected payload shape."""


class AmazonRequestBuilder(Protocol):
    def build(self, keyword: str, limit: int) -> HttpRequest:
        """Build an Amazon search request."""


@dataclass(frozen=True)
class AmazonGateway:
    request_builder: AmazonRequestBuilder
    mapper: AmazonOfferMapper = field(default_factory=AmazonOfferMapper)
    http_client: ProviderHttpClient = field(default_factory=ProviderHttpClient)
    transport: HttpTransport | None = None
    retry_policy: RetryPolicy | None = None
    sleeper: Sleeper | None = None

    def build_search_request(self, keyword: str, limit: int) -> HttpRequest:
        validate_positive_limit(limit)
        return self.request_builder.build(keyword=keyword, limit=limit)

    def execute_search(self, keyword: str, niche: str, limit: int) -> list[Offer]:
        request = self.build_search_request(keyword=keyword, limit=limit)
        response_data = execute_provider_request(
            request=request,
            transport=self.transport,
            http_client=self.http_client,
            provider_name="Amazon",
            retry_policy=self.retry_policy,
            sleeper=self.sleeper,
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
                page=page,
            )
            response_data = execute_provider_request(
                request=request,
                transport=self.transport,
                http_client=self.http_client,
                provider_name="Amazon",
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
        response_data: dict[str, Any],
        niche: str,
        limit: int,
    ) -> list[Offer]:
        validate_positive_limit(limit)
        items = self._get_items(response_data)
        return [self.mapper.map_item(item=item, niche=niche) for item in items[:limit]]

    def _build_paginated_request(
        self,
        keyword: str,
        limit: int,
        page: int,
    ) -> HttpRequest:
        request = self.build_search_request(keyword=keyword, limit=limit)
        body = dict(request.body or {})
        body["Page"] = page
        return HttpRequest(
            method=request.method,
            url=request.url,
            params=request.params,
            headers=request.headers,
            body=body,
        )

    def _has_next_page(self, response_data: dict[str, Any]) -> bool:
        return response_data.get("has_next_page") is True

    def _get_items(self, response_data: dict[str, Any]) -> list[dict[str, Any]]:
        items_result = response_data.get("SearchResult", {})
        if not isinstance(items_result, dict):
            msg = "Amazon response field 'SearchResult' must be an object"
            raise AmazonPayloadError(msg)

        items = items_result.get("Items", [])
        if not isinstance(items, list):
            msg = "Amazon response field 'SearchResult.Items' must be a list"
            raise AmazonPayloadError(msg)

        if not all(isinstance(item, dict) for item in items):
            msg = "Amazon response field 'SearchResult.Items' must contain objects"
            raise AmazonPayloadError(msg)

        return items
