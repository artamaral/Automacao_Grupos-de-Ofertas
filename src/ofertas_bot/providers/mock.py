from __future__ import annotations

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.shopee_graphql import ShopeeGraphqlOfferMapper


def build_mock_shopee_offer_connection(niche: str) -> dict[str, object]:
    return {
        "nodes": [
            {
                "commissionRate": "0.08",
                "imageUrl": "https://example.com/oferta-1.jpg",
                "offerLink": "https://example.com/oferta-1?tag=afiliado",
                "originalLink": "https://example.com/produto-1",
                "offerName": f"Kit {niche.title()} com desconto",
                "offerType": 1,
                "collectionId": 1001,
                "periodStartTime": 1_700_000_000,
                "periodEndTime": 1_700_086_400,
            },
            {
                "commissionRate": "0.05",
                "imageUrl": "https://example.com/oferta-2.jpg",
                "offerLink": "https://example.com/oferta-2?tag=afiliado",
                "originalLink": "https://example.com/produto-2",
                "offerName": f"Achadinho de {niche} popular",
                "offerType": 2,
                "categoryId": 2002,
                "periodStartTime": 1_700_000_000,
                "periodEndTime": 1_700_086_400,
            },
        ],
        "pageInfo": {
            "page": 1,
            "limit": 2,
            "hasNextPage": False,
        },
    }


class MockOfferProvider:
    def fetch(self, marketplace: Marketplace, niche: str, limit: int) -> list[Offer]:
        mapper = ShopeeGraphqlOfferMapper(marketplace=marketplace)
        connection = build_mock_shopee_offer_connection(niche)
        nodes = connection["nodes"]
        if not isinstance(nodes, list):
            return []
        catalog = [mapper.map_node(node=node, niche=niche) for node in nodes]
        return catalog[:limit]
