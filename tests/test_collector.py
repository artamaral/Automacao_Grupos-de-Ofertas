import json

import pytest

from ofertas_bot.agents.collector import CatalogSourceError, CollectorAgent
from ofertas_bot.discovery_profiles import DiscoveryProfile
from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.amazon import AmazonConfigurationError
from ofertas_bot.providers.shopee_graphql import ShopeeGraphqlPayloadError
from ofertas_bot.providers.shopee import ShopeeConfigurationError
from ofertas_bot.settings import Settings


def test_collector_uses_mock_provider_for_mock_marketplace() -> None:
    collector = CollectorAgent(settings=Settings())

    offers = collector.collect(
        marketplace=Marketplace.MOCK,
        niche="maquiagem",
        limit=1,
    )

    assert len(offers) == 1
    assert offers[0].marketplace == Marketplace.MOCK
    assert offers[0].niche == "maquiagem"
    assert offers[0].price == 0
    assert offers[0].commission_rate == 0.08
    assert offers[0].url == "https://example.com/oferta-1?tag=afiliado"


def test_collector_raises_controlled_error_for_amazon_without_configuration() -> None:
    collector = CollectorAgent(
        settings=Settings(
            amazon_access_key=None,
            amazon_secret_key=None,
            amazon_partner_tag=None,
        )
    )

    with pytest.raises(AmazonConfigurationError):
        collector.collect(
            marketplace=Marketplace.AMAZON,
            niche="casa",
            limit=1,
        )


def test_collector_raises_controlled_error_for_shopee_without_credentials() -> None:
    collector = CollectorAgent(
        settings=Settings(
            shopee_partner_id=None,
            shopee_secret_key=None,
        )
    )

    with pytest.raises(ShopeeConfigurationError):
        collector.collect(
            marketplace=Marketplace.SHOPEE,
            niche="maquiagem",
            limit=1,
        )


def test_collector_loads_offers_from_normalized_catalog_json(tmp_path) -> None:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            [
                {
                    "marketplace": "mock",
                    "title": "Bolsa maternidade",
                    "url": "https://example.com/bolsa",
                    "image_url": "https://example.com/bolsa.jpg",
                    "price": 99.9,
                    "old_price": 129.9,
                    "commission_rate": 0.12,
                    "sales_count": 10,
                    "rating": 4.8,
                    "niche": "origem",
                    "is_prime_or_free_shipping": False,
                }
            ]
        ),
        encoding="utf-8",
    )
    collector = CollectorAgent(settings=Settings())

    offers = collector.collect_from_catalog_file(
        path=catalog_path,
        niche="mae e bebe",
        marketplace=Marketplace.SHOPEE,
        limit=10,
    )

    assert len(offers) == 1
    assert offers[0].marketplace == Marketplace.SHOPEE
    assert offers[0].title == "Bolsa maternidade"
    assert offers[0].niche == "mae e bebe"
    assert offers[0].url == "https://example.com/bolsa"


def test_collector_loads_offers_from_builder_csv_and_deduplicates(tmp_path) -> None:
    catalog_path = tmp_path / "catalog.csv"
    catalog_path.write_text(
        "\n".join(
            [
                "productName,offerLink,productLink,imageUrl,price,priceMax,commissionRate,sales,ratingStar",
                "Carrinho bebe,https://example.com/item-1,https://example.com/product-1,https://example.com/item-1.jpg,100,140,0.15,25,4.9",
                "Carrinho bebe duplicado,https://example.com/item-1,https://example.com/product-1b,https://example.com/item-1b.jpg,100,140,0.15,25,4.9",
            ]
        ),
        encoding="utf-8",
    )
    collector = CollectorAgent(settings=Settings())

    offers = collector.collect_from_catalog_file(
        path=catalog_path,
        niche="mae e bebe",
        marketplace=Marketplace.SHOPEE,
        limit=10,
    )

    assert len(offers) == 1
    assert offers[0].title == "Carrinho bebe"
    assert offers[0].old_price == 140.0
    assert offers[0].commission_rate == 0.15
    assert offers[0].sales_count == 25


def test_collector_rejects_catalog_without_supported_format(tmp_path) -> None:
    catalog_path = tmp_path / "catalog.txt"
    catalog_path.write_text("invalid", encoding="utf-8")
    collector = CollectorAgent(settings=Settings())

    with pytest.raises(CatalogSourceError):
        collector.collect_from_catalog_file(
            path=catalog_path,
            niche="mae e bebe",
            marketplace=Marketplace.SHOPEE,
            limit=10,
        )


def test_collector_uses_descobridor_geral_for_shopee_profile() -> None:
    class FakeShopeeProvider:
        seen_offer_limits: list[int] = []

        def fetch_offer_search_raw_response(self, offer_name: str, limit: int) -> dict[str, object]:
            self.seen_offer_limits.append(limit)
            return {
                "data": {
                    "shopeeOfferV2": {
                        "nodes": [{"categoryId": 100632, "offerName": offer_name}],
                        "pageInfo": {"page": 1, "limit": limit, "hasNextPage": False},
                    }
                }
            }

        def fetch_product_match_raw_response(
            self,
            match_id: int,
            limit: int,
            *,
            page: int = 1,
        ) -> dict[str, object]:
            return {
                "data": {
                    "productOfferV2": {
                        "nodes": [
                            {
                                "productName": "Bolsa maternidade",
                                "offerLink": "https://s.shopee.com.br/exemplo",
                                "imageUrl": "https://example.com/item.jpg",
                                "commissionRate": "0.25",
                            }
                        ],
                        "pageInfo": {"page": page, "limit": limit, "hasNextPage": False},
                    }
                }
            }

        def normalize_custom_response(
            self,
            *,
            response_data: dict[str, object],
            niche: str,
            limit: int,
            root_field: str,
        ) -> list[Offer]:
            assert root_field == "productOfferV2"
            return [
                Offer(
                    marketplace=Marketplace.SHOPEE,
                    title="Bolsa maternidade",
                    url="https://s.shopee.com.br/exemplo",
                    image_url="https://example.com/item.jpg",
                    price=0,
                    old_price=None,
                    commission_rate=0.25,
                    sales_count=0,
                    rating=None,
                    niche=niche,
                )
            ][:limit]

    collector = CollectorAgent(settings=Settings())
    object.__setattr__(collector, "_shopee_provider", FakeShopeeProvider())
    profile = DiscoveryProfile(
        slug="mae-e-bebe",
        name="Mae e Bebe",
        niche="mae e bebe",
        marketplace=Marketplace.SHOPEE,
        discovery_method="descobridor-geral",
        shopee_offer_keyword="Mom & Baby",
    )

    batch = collector.collect_from_profile_with_inspection(profile=profile, limit=1)

    assert len(batch.offers) == 1
    assert batch.offers[0].title == "Bolsa maternidade"
    assert batch.raw_response is not None
    assert batch.raw_response["discovery_method"] == "descobridor-geral"
    assert batch.raw_response["selected_match_ids"] == [100632]
    assert batch.raw_response["offer_search_limit"] == 50
    assert collector._shopee_provider.seen_offer_limits == [1]


def test_collector_descobridor_geral_caps_offer_search_limit_at_50() -> None:
    class FakeShopeeProvider:
        seen_offer_limits: list[int] = []

        def fetch_offer_search_raw_response(self, offer_name: str, limit: int) -> dict[str, object]:
            self.seen_offer_limits.append(limit)
            return {
                "data": {
                    "shopeeOfferV2": {
                        "nodes": [{"categoryId": 100632, "offerName": offer_name}],
                        "pageInfo": {"page": 1, "limit": limit, "hasNextPage": False},
                    }
                }
            }

        def fetch_product_match_raw_response(
            self,
            match_id: int | None,
            limit: int,
            *,
            page: int = 1,
            list_type: int = 4,
            sort_type: int | None = None,
            is_key_seller: bool | None = None,
        ) -> dict[str, object]:
            return {
                "data": {
                    "productOfferV2": {
                        "nodes": [],
                        "pageInfo": {"page": page, "limit": limit, "hasNextPage": False},
                    }
                }
            }

        def normalize_custom_response(
            self,
            *,
            response_data: dict[str, object],
            niche: str,
            limit: int,
            root_field: str,
        ) -> list[Offer]:
            return []

    collector = CollectorAgent(settings=Settings())
    object.__setattr__(collector, "_shopee_provider", FakeShopeeProvider())
    profile = DiscoveryProfile(
        slug="pets",
        name="Pets",
        niche="pets",
        marketplace=Marketplace.SHOPEE,
        discovery_method="descobridor-geral",
        shopee_offer_keyword="Pets",
    )

    batch = collector.collect_from_profile_with_inspection(profile=profile, limit=3000)

    assert batch.raw_response is not None
    assert batch.raw_response["offer_search_limit"] == 50
    assert collector._shopee_provider.seen_offer_limits == [50]


def test_collector_descobridor_geral_paginates_until_has_next_page_is_false() -> None:
    class FakeShopeeProvider:
        def fetch_offer_search_raw_response(self, offer_name: str, limit: int) -> dict[str, object]:
            return {
                "data": {
                    "shopeeOfferV2": {
                        "nodes": [{"categoryId": 100632, "offerName": offer_name}],
                        "pageInfo": {"page": 1, "limit": limit, "hasNextPage": False},
                    }
                }
            }

        def fetch_product_match_raw_response(
            self,
            match_id: int,
            limit: int,
            *,
            page: int = 1,
        ) -> dict[str, object]:
            has_next = page < 3
            return {
                "data": {
                    "productOfferV2": {
                        "nodes": [
                            {
                                "productName": f"Produto pagina {page}",
                                "offerLink": f"https://s.shopee.com.br/item-{page}",
                                "imageUrl": "https://example.com/item.jpg",
                                "commissionRate": "0.25",
                            }
                        ],
                        "pageInfo": {"page": page, "limit": limit, "hasNextPage": has_next},
                    }
                }
            }

        def normalize_custom_response(
            self,
            *,
            response_data: dict[str, object],
            niche: str,
            limit: int,
            root_field: str,
        ) -> list[Offer]:
            node = response_data["data"]["productOfferV2"]["nodes"][0]
            return [
                Offer(
                    marketplace=Marketplace.SHOPEE,
                    title=str(node["productName"]),
                    url=str(node["offerLink"]),
                    image_url=str(node["imageUrl"]),
                    price=0,
                    old_price=None,
                    commission_rate=0.25,
                    sales_count=0,
                    rating=None,
                    niche=niche,
                )
            ]

    collector = CollectorAgent(settings=Settings())
    object.__setattr__(collector, "_shopee_provider", FakeShopeeProvider())
    profile = DiscoveryProfile(
        slug="mae-e-bebe",
        name="Mae e Bebe",
        niche="mae e bebe",
        marketplace=Marketplace.SHOPEE,
        discovery_method="descobridor-geral",
        shopee_offer_keyword="Mom & Baby",
    )

    batch = collector.collect_from_profile_with_inspection(profile=profile, limit=10)

    assert [offer.title for offer in batch.offers] == [
        "Produto pagina 1",
        "Produto pagina 2",
        "Produto pagina 3",
    ]
    assert batch.raw_response is not None
    assert batch.raw_response["product_searches"][0]["pages"][-1]["hasNextPage"] is False


def test_collector_descobridor_geral_stops_on_page_not_found() -> None:
    class FakeShopeeProvider:
        def fetch_offer_search_raw_response(self, offer_name: str, limit: int) -> dict[str, object]:
            return {
                "data": {
                    "shopeeOfferV2": {
                        "nodes": [{"categoryId": 100632, "offerName": offer_name}],
                        "pageInfo": {"page": 1, "limit": limit, "hasNextPage": False},
                    }
                }
            }

        def fetch_product_match_raw_response(
            self,
            match_id: int,
            limit: int,
            *,
            page: int = 1,
        ) -> dict[str, object]:
            if page == 2:
                raise ShopeeGraphqlPayloadError("error [10010]: page not found")
            return {
                "data": {
                    "productOfferV2": {
                        "nodes": [
                            {
                                "productName": "Primeira pagina",
                                "offerLink": "https://s.shopee.com.br/item-1",
                                "imageUrl": "https://example.com/item.jpg",
                                "commissionRate": "0.25",
                            }
                        ],
                        "pageInfo": {"page": page, "limit": limit, "hasNextPage": True},
                    }
                }
            }

        def normalize_custom_response(
            self,
            *,
            response_data: dict[str, object],
            niche: str,
            limit: int,
            root_field: str,
        ) -> list[Offer]:
            node = response_data["data"]["productOfferV2"]["nodes"][0]
            return [
                Offer(
                    marketplace=Marketplace.SHOPEE,
                    title=str(node["productName"]),
                    url=str(node["offerLink"]),
                    image_url=str(node["imageUrl"]),
                    price=0,
                    old_price=None,
                    commission_rate=0.25,
                    sales_count=0,
                    rating=None,
                    niche=niche,
                )
            ]

    collector = CollectorAgent(settings=Settings())
    object.__setattr__(collector, "_shopee_provider", FakeShopeeProvider())
    profile = DiscoveryProfile(
        slug="mae-e-bebe",
        name="Mae e Bebe",
        niche="mae e bebe",
        marketplace=Marketplace.SHOPEE,
        discovery_method="descobridor-geral",
        shopee_offer_keyword="Mom & Baby",
    )

    batch = collector.collect_from_profile_with_inspection(profile=profile, limit=10)

    assert [offer.title for offer in batch.offers] == ["Primeira pagina"]
    assert batch.raw_response is not None
    assert batch.raw_response["product_searches"][0]["pages"][-1]["stopped_by"] == "page_not_found"
