import pytest

from ofertas_bot.models import Marketplace
from ofertas_bot.providers.http import HttpResponse
from ofertas_bot.providers.shopee_gateway import ShopeeGateway
from ofertas_bot.providers.shopee_signed_request import ShopeeSignedRequestBuilder
from ofertas_bot.providers.transport import StaticHttpTransport


def test_shopee_gateway_builds_search_request() -> None:
    gateway = ShopeeGateway(
        request_builder=ShopeeSignedRequestBuilder(
            partner_id="123",
            api_credential="abc",
            base_url="https://example.com",
        )
    )

    request = gateway.build_search_request(
        keyword="maquiagem",
        limit=10,
        timestamp=1710000000,
    )

    assert request.method == "GET"
    assert request.params["keyword"] == "maquiagem"
    assert request.params["page_size"] == 10
    assert request.params["partner_id"] == "123"


def test_shopee_gateway_executes_search_with_static_transport() -> None:
    response = HttpResponse(
        status_code=200,
        data={
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
                }
            ]
        },
    )
    transport = StaticHttpTransport(response=response)
    gateway = ShopeeGateway(
        request_builder=ShopeeSignedRequestBuilder(
            partner_id="123",
            api_credential="abc",
            base_url="https://example.com",
        ),
        transport=transport,
    )

    offers = gateway.execute_search(
        keyword="maquiagem",
        niche="maquiagem",
        limit=1,
        timestamp=1710000000,
    )

    assert len(offers) == 1
    assert offers[0].marketplace == Marketplace.SHOPEE
    assert offers[0].title == "Kit Maquiagem"
    assert transport.requests[0].params["keyword"] == "maquiagem"


def test_shopee_gateway_requires_transport_to_execute_search() -> None:
    gateway = ShopeeGateway(
        request_builder=ShopeeSignedRequestBuilder(
            partner_id="123",
            api_credential="abc",
            base_url="https://example.com",
        )
    )

    with pytest.raises(RuntimeError, match="transport"):
        gateway.execute_search(
            keyword="maquiagem",
            niche="maquiagem",
            limit=1,
            timestamp=1710000000,
        )


def test_shopee_gateway_normalizes_search_response() -> None:
    gateway = ShopeeGateway(
        request_builder=ShopeeSignedRequestBuilder(
            partner_id="123",
            api_credential="abc",
            base_url="https://example.com",
        )
    )
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
            }
        ]
    }

    offers = gateway.normalize_search_response(
        response_data=response_data,
        niche="maquiagem",
        limit=1,
    )

    assert len(offers) == 1
    assert offers[0].marketplace == Marketplace.SHOPEE
    assert offers[0].title == "Kit Maquiagem"
