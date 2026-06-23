from dataclasses import dataclass, field
from typing import Protocol

from ofertas_bot.models import Offer
from ofertas_bot.providers.gateway import execute_provider_request, validate_positive_limit
from ofertas_bot.providers.http import HttpRequest, ProviderHttpClient
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

    def execute_search(
        self,
        keyword: str,
        niche: str,
        limit: int,
        timestamp: int,
    ) -> list[Offer]:
        request = self.build_search_request(
            keyword=keyword,
            limit=limit,
            timestamp=timestamp,
        )
        response_data = execute_provider_request(
            request=request,
            transport=self.transport,
            http_client=self.http_client,
            provider_name="Shopee",
        )
        return self.normalize_search_response(
            response_data=response_data,
            niche=niche,
            limit=limit,
        )

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
