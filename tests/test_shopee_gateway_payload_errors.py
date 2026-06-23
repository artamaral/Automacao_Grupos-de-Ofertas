import pytest

from ofertas_bot.providers.http import HttpRequest, HttpResponse
from ofertas_bot.providers.shopee_gateway import ShopeeGateway, ShopeePayloadError
from ofertas_bot.providers.transport import StaticHttpTransport


class DummyRequestBuilder:
    def build(self, keyword: str, limit: int, timestamp: int) -> HttpRequest:
        return HttpRequest(
            method="GET",
            url="https://example.com",
            params={
                "keyword": keyword,
                "page_size": limit,
                "timestamp": timestamp,
            },
        )


def test_shopee_gateway_rejects_invalid_payload_shape_after_success_response() -> None:
    response = HttpResponse(status_code=200, data={"items": {}})
    transport = StaticHttpTransport(response=response)
    gateway = ShopeeGateway(request_builder=DummyRequestBuilder(), transport=transport)

    with pytest.raises(ShopeePayloadError, match="items"):
        gateway.execute_search(
            keyword="maquiagem",
            niche="maquiagem",
            limit=1,
            timestamp=1710000000,
        )

    assert transport.requests[0].params["keyword"] == "maquiagem"
