from dataclasses import dataclass, field
from typing import Any, Protocol

from ofertas_bot.models import Offer
from ofertas_bot.providers.amazon_mapper import AmazonOfferMapper
from ofertas_bot.providers.http import HttpRequest, ProviderHttpClient
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

    def build_search_request(self, keyword: str, limit: int) -> HttpRequest:
        return self.request_builder.build(keyword=keyword, limit=limit)

    def execute_search(self, keyword: str, niche: str, limit: int) -> list[Offer]:
        if self.transport is None:
            msg = "Amazon gateway transport is not configured"
            raise RuntimeError(msg)

        request = self.build_search_request(keyword=keyword, limit=limit)
        response = self.transport.send(request)
        response_data = self.http_client.validate_response(response, provider_name="Amazon")
        return self.normalize_search_response(
            response_data=response_data,
            niche=niche,
            limit=limit,
        )

    def normalize_search_response(
        self,
        response_data: dict[str, Any],
        niche: str,
        limit: int,
    ) -> list[Offer]:
        items = self._get_items(response_data)
        return [self.mapper.map_item(item=item, niche=niche) for item in items[:limit]]

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
