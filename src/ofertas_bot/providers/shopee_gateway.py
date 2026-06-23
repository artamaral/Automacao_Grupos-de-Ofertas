from dataclasses import dataclass

from ofertas_bot.models import Offer
from ofertas_bot.providers.http import HttpRequest
from ofertas_bot.providers.shopee_mapper import ShopeeOfferMapper
from ofertas_bot.providers.shopee_signed_request import ShopeeSignedRequestBuilder


@dataclass(frozen=True)
class ShopeeGateway:
    request_builder: ShopeeSignedRequestBuilder
    mapper: ShopeeOfferMapper = ShopeeOfferMapper()

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
