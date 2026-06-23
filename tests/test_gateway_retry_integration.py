from dataclasses import dataclass, field

from ofertas_bot.providers.amazon_gateway import AmazonGateway
from ofertas_bot.providers.amazon_request import AmazonSearchRequestBuilder
from ofertas_bot.providers.http import HttpRequest, HttpResponse
from ofertas_bot.providers.retry import RetryPolicy
from ofertas_bot.providers.shopee_gateway import ShopeeGateway
from ofertas_bot.providers.shopee_signed_request import ShopeeSignedRequestBuilder


@dataclass
class SequentialTransport:
    responses: list[HttpResponse]
    requests: list[HttpRequest] = field(default_factory=list)

    def send(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        return self.responses.pop(0)


@dataclass
class RecordingSleeper:
    delays: list[float] = field(default_factory=list)

    def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)


def test_shopee_gateway_uses_optional_retry_policy() -> None:
    transport = SequentialTransport(
        responses=[
            HttpResponse(status_code=429, data={"error": "rate limit"}),
            HttpResponse(
                status_code=200,
                data={
                    "items": [
                        {
                            "title": "Oferta Shopee Retry",
                            "url": "https://example.com/shopee/retry",
                            "price": 10.0,
                            "old_price": 20.0,
                            "commission_rate": 0.05,
                            "sales_count": 10,
                        }
                    ]
                },
            ),
        ]
    )
    sleeper = RecordingSleeper()
    gateway = ShopeeGateway(
        request_builder=ShopeeSignedRequestBuilder(
            partner_id="partner",
            api_credential="credential",
            base_url="https://example.com",
        ),
        transport=transport,
        retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0.25),
        sleeper=sleeper,
    )

    offers = gateway.execute_search(
        keyword="maquiagem",
        niche="maquiagem",
        limit=1,
        timestamp=1700000000,
    )

    assert len(offers) == 1
    assert offers[0].title == "Oferta Shopee Retry"
    assert len(transport.requests) == 2
    assert sleeper.delays == [0.25]


def test_amazon_gateway_uses_optional_retry_policy() -> None:
    transport = SequentialTransport(
        responses=[
            HttpResponse(status_code=429, data={"error": "rate limit"}),
            HttpResponse(
                status_code=200,
                data={
                    "SearchResult": {
                        "Items": [
                            {
                                "DetailPageURL": "https://example.com/amazon/retry",
                                "ItemInfo": {
                                    "Title": {"DisplayValue": "Oferta Amazon Retry"}
                                },
                                "Offers": {
                                    "Listings": [{"Price": {"Amount": 15.0}}]
                                },
                            }
                        ]
                    }
                },
            ),
        ]
    )
    sleeper = RecordingSleeper()
    gateway = AmazonGateway(
        request_builder=AmazonSearchRequestBuilder(
            partner_tag="tag-20",
            base_url="https://example.com",
        ),
        transport=transport,
        retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0.25),
        sleeper=sleeper,
    )

    offers = gateway.execute_search(keyword="casa", niche="casa", limit=1)

    assert len(offers) == 1
    assert offers[0].title == "Oferta Amazon Retry"
    assert len(transport.requests) == 2
    assert sleeper.delays == [0.25]
