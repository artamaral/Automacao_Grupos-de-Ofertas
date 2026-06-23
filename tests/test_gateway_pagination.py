from dataclasses import dataclass, field

from ofertas_bot.providers.amazon_gateway import AmazonGateway
from ofertas_bot.providers.amazon_request import AmazonSearchRequestBuilder
from ofertas_bot.providers.http import HttpRequest, HttpResponse
from ofertas_bot.providers.shopee_gateway import ShopeeGateway
from ofertas_bot.providers.shopee_signed_request import ShopeeSignedRequestBuilder


@dataclass
class SequentialTransport:
    responses: list[HttpResponse]
    requests: list[HttpRequest] = field(default_factory=list)

    def send(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        return self.responses.pop(0)


def shopee_item(title: str) -> dict[str, object]:
    return {
        "title": title,
        "url": f"https://example.com/shopee/{title}",
        "price": 10.0,
        "old_price": 20.0,
        "commission_rate": 0.05,
        "sales_count": 10,
    }


def amazon_item(title: str) -> dict[str, object]:
    return {
        "DetailPageURL": f"https://example.com/amazon/{title}",
        "ItemInfo": {"Title": {"DisplayValue": title}},
        "Offers": {"Listings": [{"Price": {"Amount": 15.0}}]},
    }


def make_shopee_gateway(transport: SequentialTransport) -> ShopeeGateway:
    return ShopeeGateway(
        request_builder=ShopeeSignedRequestBuilder(
            partner_id="partner",
            api_credential="credential",
            base_url="https://example.com",
        ),
        transport=transport,
    )


def make_amazon_gateway(transport: SequentialTransport) -> AmazonGateway:
    return AmazonGateway(
        request_builder=AmazonSearchRequestBuilder(
            partner_tag="tag-20",
            base_url="https://example.com",
        ),
        transport=transport,
    )


def test_shopee_gateway_collects_paginated_fake_responses() -> None:
    transport = SequentialTransport(
        responses=[
            HttpResponse(
                status_code=200,
                data={"items": [shopee_item("Oferta 1")], "has_next_page": True},
            ),
            HttpResponse(
                status_code=200,
                data={"items": [shopee_item("Oferta 2")], "has_next_page": False},
            ),
        ]
    )
    gateway = make_shopee_gateway(transport)

    offers = gateway.execute_paginated_search(
        keyword="maquiagem",
        niche="maquiagem",
        limit=2,
        page_size=1,
        timestamp=1700000000,
    )

    assert [offer.title for offer in offers] == ["Oferta 1", "Oferta 2"]
    assert [request.params["page"] for request in transport.requests] == [1, 2]
    assert [request.params["page_size"] for request in transport.requests] == [1, 1]


def test_shopee_gateway_stops_at_max_pages() -> None:
    transport = SequentialTransport(
        responses=[
            HttpResponse(
                status_code=200,
                data={"items": [shopee_item("Oferta 1")], "has_next_page": True},
            ),
        ]
    )
    gateway = make_shopee_gateway(transport)

    offers = gateway.execute_paginated_search(
        keyword="maquiagem",
        niche="maquiagem",
        limit=3,
        page_size=1,
        timestamp=1700000000,
        max_pages=1,
    )

    assert [offer.title for offer in offers] == ["Oferta 1"]
    assert len(transport.requests) == 1
    assert transport.requests[0].params["page"] == 1


def test_shopee_gateway_stops_on_empty_page() -> None:
    transport = SequentialTransport(
        responses=[
            HttpResponse(
                status_code=200,
                data={"items": [], "has_next_page": True},
            ),
        ]
    )
    gateway = make_shopee_gateway(transport)

    offers = gateway.execute_paginated_search(
        keyword="maquiagem",
        niche="maquiagem",
        limit=3,
        page_size=1,
        timestamp=1700000000,
    )

    assert offers == []
    assert len(transport.requests) == 1


def test_amazon_gateway_collects_paginated_fake_responses() -> None:
    transport = SequentialTransport(
        responses=[
            HttpResponse(
                status_code=200,
                data={
                    "SearchResult": {"Items": [amazon_item("Oferta 1")]},
                    "has_next_page": True,
                },
            ),
            HttpResponse(
                status_code=200,
                data={
                    "SearchResult": {"Items": [amazon_item("Oferta 2")]},
                    "has_next_page": False,
                },
            ),
        ]
    )
    gateway = make_amazon_gateway(transport)

    offers = gateway.execute_paginated_search(
        keyword="casa",
        niche="casa",
        limit=2,
        page_size=1,
    )

    assert [offer.title for offer in offers] == ["Oferta 1", "Oferta 2"]
    assert [request.body["Page"] for request in transport.requests if request.body] == [1, 2]
    assert [request.body["ItemCount"] for request in transport.requests if request.body] == [
        1,
        1,
    ]


def test_amazon_gateway_stops_at_max_pages() -> None:
    transport = SequentialTransport(
        responses=[
            HttpResponse(
                status_code=200,
                data={
                    "SearchResult": {"Items": [amazon_item("Oferta 1")]},
                    "has_next_page": True,
                },
            ),
        ]
    )
    gateway = make_amazon_gateway(transport)

    offers = gateway.execute_paginated_search(
        keyword="casa",
        niche="casa",
        limit=3,
        page_size=1,
        max_pages=1,
    )

    assert [offer.title for offer in offers] == ["Oferta 1"]
    assert len(transport.requests) == 1
    assert transport.requests[0].body is not None
    assert transport.requests[0].body["Page"] == 1


def test_amazon_gateway_stops_on_empty_page() -> None:
    transport = SequentialTransport(
        responses=[
            HttpResponse(
                status_code=200,
                data={"SearchResult": {"Items": []}, "has_next_page": True},
            ),
        ]
    )
    gateway = make_amazon_gateway(transport)

    offers = gateway.execute_paginated_search(
        keyword="casa",
        niche="casa",
        limit=3,
        page_size=1,
    )

    assert offers == []
    assert len(transport.requests) == 1
