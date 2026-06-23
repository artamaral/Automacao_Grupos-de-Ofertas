import pytest

from ofertas_bot.models import Marketplace
from ofertas_bot.providers.amazon import AmazonConfigurationError, AmazonProvider
from ofertas_bot.providers.amazon_gateway import AmazonGateway
from ofertas_bot.providers.amazon_request import AmazonSearchRequestBuilder
from ofertas_bot.providers.http import HttpResponse
from ofertas_bot.providers.transport import StaticHttpTransport
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


def test_amazon_provider_fetch_uses_injected_gateway() -> None:
    response = HttpResponse(
        status_code=200,
        data={
            "SearchResult": {
                "Items": [
                    {
                        "ItemInfo": {"Title": {"DisplayValue": "Produto Casa"}},
                        "DetailPageURL": "https://example.com/amazon-1",
                        "Offers": {
                            "Listings": [
                                {
                                    "Price": {"Amount": 79.9},
                                    "SavingBasis": {"Amount": 119.9},
                                }
                            ]
                        },
                    }
                ]
            }
        },
    )
    transport = StaticHttpTransport(response=response)
    gateway = AmazonGateway(
        request_builder=AmazonSearchRequestBuilder(
            partner_tag="tag-20",
            base_url="https://example.com",
        ),
        transport=transport,
    )
    settings = Settings(
        amazon_access_key="configured",
        amazon_secret_key="configured",
        amazon_partner_tag="tag-20",
    )
    provider = AmazonProvider(settings=settings, gateway=gateway)

    offers = provider.fetch(niche="casa", limit=1)

    assert len(offers) == 1
    assert offers[0].marketplace == Marketplace.AMAZON
    assert offers[0].title == "Produto Casa"
    assert transport.requests[0].body is not None
    assert transport.requests[0].body["Keywords"] == "casa"
