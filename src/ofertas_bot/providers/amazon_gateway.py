from dataclasses import dataclass, field
from typing import Protocol, Any

from ofertas_bot.providers.amazon_request import AmazonSearchRequestBuilder
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
    http_client: ProviderHttpClient = field(default_factory=ProviderHttpClient)
    transport: HttpTransport | None = None

    def build_search_request(self, keyword: str, limit: int) -> HttpRequest:
        return self.request_builder.build(keyword=keyword, limit=limit)

    def execute_search(self, keyword: str, limit: int) -> dict[str, Any]:
        if self.transport is None:
            msg = "Amazon gateway transport is not configured"
            raise RuntimeError(msg)

        request = self.build_search_request(keyword=keyword, limit=limit)
        response = self.transport.send(request)
        response_data = self.http_client.validate_response(response, provider_name="Amazon")
        self._validate_search_response(response_data)
        return response_data

    def _validate_search_response(self, response_data: dict[str, Any]) -> None:
        items_result = response_data.get("SearchResult", {})
        if not isinstance(items_result, dict):
            msg = "Amazon response field 'SearchResult' must be an object"
            raise AmazonPayloadError(msg)

        items = items_result.get("Items", [])
        if not isinstance(items, list):
            msg = "Amazon response field 'SearchResult.Items' must be a list"
            raise AmazonPayloadError(msg)
