import pytest

from ofertas_bot.agents.collector import CollectorAgent
from ofertas_bot.models import Marketplace
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
