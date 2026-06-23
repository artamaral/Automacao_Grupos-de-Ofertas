import pytest

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
        shopee_partner_id="partner-id",
        shopee_secret_key="secret-key",
    )
    provider = ShopeeProvider(settings=settings)

    with pytest.raises(NotImplementedError):
        provider.fetch(niche="maquiagem", limit=3)
