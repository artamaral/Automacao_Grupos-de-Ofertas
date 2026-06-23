import pytest

from ofertas_bot.models import Marketplace
from ofertas_bot.providers.shopee import ShopeeConfigurationError, ShopeeProvider
from ofertas_bot.settings import Settings


def test_shopee_provider_requires_credentials() -> None:
    settings = Settings(
        shopee_partner_id=None,
        shopee_secret_key=None,
    )
    provider = ShopeeProvider(settings=settings)

    with pytest.raises(ShopeeConfigurationError) as error:
        provider.fetch(niche="maquiagem", limit=3)

    message = str(error.value)
    assert "SHOPEE_PARTNER_ID" in message
    assert "SHOPEE_SECRET_KEY" in message


def test_shopee_provider_is_not_implemented_after_configuration() -> None:
    settings = Settings(
        shopee_partner_id="configured",
        shopee_secret_key="configured",
    )
    provider = ShopeeProvider(settings=settings)

    with pytest.raises(NotImplementedError):
        provider.fetch(niche="maquiagem", limit=3)


def test_shopee_provider_normalizes_response_items() -> None:
    provider = ShopeeProvider(settings=Settings())
    response_data = {
        "items": [
            {
                "title": "Kit Maquiagem",
                "url": "https://example.com/shopee-1",
                "price": "49.90",
                "old_price": "89.90",
                "commission_rate": "0.08",
                "sales_count": "1200",
                "rating": "4.8",
                "is_free_shipping": True,
            },
            {
                "title": "Oferta ignorada pelo limite",
                "url": "https://example.com/shopee-2",
                "price": "10",
                "old_price": "20",
            },
        ]
    }

    offers = provider.normalize_response(response_data=response_data, niche="maquiagem", limit=1)

    assert len(offers) == 1
    assert offers[0].marketplace == Marketplace.SHOPEE
    assert offers[0].title == "Kit Maquiagem"
    assert offers[0].discount_percent == 44.49


def test_shopee_provider_rejects_invalid_items_shape() -> None:
    provider = ShopeeProvider(settings=Settings())

    with pytest.raises(ValueError, match="items"):
        provider.normalize_response(response_data={"items": {}}, niche="maquiagem", limit=1)
