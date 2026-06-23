from ofertas_bot.providers.amazon_gateway import AmazonGateway
from ofertas_bot.providers.amazon_request import AmazonSearchRequestBuilder
from ofertas_bot.providers.http import HttpResponse
from ofertas_bot.providers.shopee_gateway import ShopeeGateway
from ofertas_bot.providers.shopee_signed_request import ShopeeSignedRequestBuilder
from ofertas_bot.providers.transport import StaticHttpTransport


def test_shopee_gateway_returns_empty_list_for_empty_items() -> None:
    response = HttpResponse(status_code=200, data={"items": []})
    gateway = ShopeeGateway(
        request_builder=ShopeeSignedRequestBuilder(
            partner_id="partner",
            api_credential="credential",
            base_url="https://example.com",
        ),
        transport=StaticHttpTransport(response=response),
    )

    offers = gateway.execute_search(
        keyword="maquiagem",
        niche="maquiagem",
        limit=5,
        timestamp=1700000000,
    )

    assert offers == []


def test_amazon_gateway_returns_empty_list_for_empty_items() -> None:
    response = HttpResponse(status_code=200, data={"SearchResult": {"Items": []}})
    gateway = AmazonGateway(
        request_builder=AmazonSearchRequestBuilder(
            partner_tag="tag-20",
            base_url="https://example.com",
        ),
        transport=StaticHttpTransport(response=response),
    )

    offers = gateway.execute_search(keyword="casa", niche="casa", limit=5)

    assert offers == []
