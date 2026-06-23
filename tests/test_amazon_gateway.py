import pytest

from ofertas_bot.models import Marketplace
from ofertas_bot.providers.amazon_gateway import AmazonGateway, AmazonPayloadError
from ofertas_bot.providers.amazon_request import AmazonSearchRequestBuilder
from ofertas_bot.providers.http import HttpResponse, ProviderHttpError
from ofertas_bot.providers.transport import StaticHttpTransport


def test_amazon_gateway_builds_search_request() -> None:
    gateway = AmazonGateway(
        request_builder=AmazonSearchRequestBuilder(
            partner_tag="tag-20",
            base_url="https://example.com",
        )
    )

    request = gateway.build_search_request(keyword="maquiagem", limit=10)

    assert request.method == "POST"
    assert request.body is not None
    assert request.body["Keywords"] == "maquiagem"
    assert request.body["ItemCount"] == 10


def test_amazon_gateway_executes_search_with_static_transport() -> None:
    response = HttpResponse(
        status_code=200,
        data={
            "SearchResult": {
                "Items": [
                    {
                        "ItemInfo": {"Title": {"DisplayValue": "Kit Amazon"}},
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

    offers = gateway.execute_search(keyword="maquiagem", niche="maquiagem", limit=1)

    assert len(offers) == 1
    assert offers[0].marketplace == Marketplace.AMAZON
    assert offers[0].title == "Kit Amazon"
    assert offers[0].price == 79.9
    assert transport.requests[0].body is not None
    assert transport.requests[0].body["Keywords"] == "maquiagem"


def test_amazon_gateway_rejects_http_error_response() -> None:
    response = HttpResponse(status_code=500, data={"SearchResult": {"Items": []}})
    transport = StaticHttpTransport(response=response)
    gateway = AmazonGateway(
        request_builder=AmazonSearchRequestBuilder(
            partner_tag="tag-20",
            base_url="https://example.com",
        ),
        transport=transport,
    )

    with pytest.raises(ProviderHttpError, match="Amazon request failed with status=500"):
        gateway.execute_search(keyword="maquiagem", niche="maquiagem", limit=1)


def test_amazon_gateway_rejects_invalid_payload_shape() -> None:
    response = HttpResponse(status_code=200, data={"SearchResult": {"Items": {}}})
    transport = StaticHttpTransport(response=response)
    gateway = AmazonGateway(
        request_builder=AmazonSearchRequestBuilder(
            partner_tag="tag-20",
            base_url="https://example.com",
        ),
        transport=transport,
    )

    with pytest.raises(AmazonPayloadError, match="SearchResult.Items"):
        gateway.execute_search(keyword="maquiagem", niche="maquiagem", limit=1)


def test_amazon_gateway_rejects_items_with_invalid_shape() -> None:
    response = HttpResponse(status_code=200, data={"SearchResult": {"Items": ["bad"]}})
    transport = StaticHttpTransport(response=response)
    gateway = AmazonGateway(
        request_builder=AmazonSearchRequestBuilder(
            partner_tag="tag-20",
            base_url="https://example.com",
        ),
        transport=transport,
    )

    with pytest.raises(AmazonPayloadError, match="contain objects"):
        gateway.execute_search(keyword="maquiagem", niche="maquiagem", limit=1)


def test_amazon_gateway_requires_transport_to_execute_search() -> None:
    gateway = AmazonGateway(
        request_builder=AmazonSearchRequestBuilder(
            partner_tag="tag-20",
            base_url="https://example.com",
        )
    )

    with pytest.raises(RuntimeError, match="transport"):
        gateway.execute_search(keyword="maquiagem", niche="maquiagem", limit=1)
