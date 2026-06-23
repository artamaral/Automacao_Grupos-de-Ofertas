from dataclasses import dataclass, field

from ofertas_bot.models import Offer
from ofertas_bot.providers.http import HttpRequest, ProviderHttpClient
from ofertas_bot.providers.shopee_mapper import ShopeeOfferMapper
from ofertas_bot.providers.shopee_signed_request import ShopeeSignedRequestBuilder
from ofertas_bot.providers.transport import HttpTransport


@dataclass(frozen=True)
class ShopeeGateway:
    request_builder: ShopeeSignedRequestBuilder
    mapper: ShopeeOfferMapper = field(default_factory=ShopeeOfferMapper)
    http_client: ProviderHttpClient = field(default_factory=ProviderHttpClient)
    transport: HttpTransport | None = None

    def build_search_request(
        self,
        keyword: str,
        limit: int,
        timestamp: int,
    ) -> HttpRequest:
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
        if self.transport is None:
            msg = "Shopee gateway transport is not configured"
            raise RuntimeError(msg)

        request = self.build_search_request(
            keyword=keyword,
            limit=limit,
            timestamp=timestamp,
        )
        response = self.transport.send(request)
        response_data = self.http_client.validate_response(response, provider_name="Shopee")
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
        items = response_data.get("items", [])
        if not isinstance(items, list):
            msg = "Shopee response field 'items' must be a list"
            raise ValueError(msg)

        return [self.mapper.map_item(item=item, niche=niche) for item in items[:limit]]
