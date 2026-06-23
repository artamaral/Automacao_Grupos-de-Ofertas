import pytest

from ofertas_bot.providers.amazon import AmazonConfigurationError, AmazonProvider
from ofertas_bot.settings import Settings


def test_amazon_provider_requires_configuration() -> None:
    settings = Settings(
        amazon_access_key=None,
        amazon_secret_key=None,
        amazon_partner_tag=None,
    )
    provider = AmazonProvider(settings=settings)

    with pytest.raises(AmazonConfigurationError) as error:
        provider.fetch(niche="casa", limit=3)

    message = str(error.value)
    assert "AMAZON_ACCESS_KEY" in message
    assert "AMAZON_SECRET_KEY" in message
    assert "AMAZON_PARTNER_TAG" in message


def test_amazon_provider_is_pending_after_configuration() -> None:
    settings = Settings(
        amazon_access_key="configured",
        amazon_secret_key="configured",
        amazon_partner_tag="configured",
    )
    provider = AmazonProvider(settings=settings)

    with pytest.raises(NotImplementedError):
        provider.fetch(niche="casa", limit=3)
