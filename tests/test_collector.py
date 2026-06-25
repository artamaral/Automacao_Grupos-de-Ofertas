import pytest

from ofertas_bot.agents.collector import CollectorAgent
from ofertas_bot.discovery_profiles import DiscoveryProfile
from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.amazon import AmazonConfigurationError
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


def test_collector_uses_descobridor_geral_for_shopee_profile() -> None:
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

        def fetch_product_match_raw_response(self, match_id: int, limit: int) -> dict[str, object]:
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
                        "pageInfo": {"page": 1, "limit": limit, "hasNextPage": False},
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
