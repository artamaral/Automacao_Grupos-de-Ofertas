import json
from pathlib import Path
from typing import Any

from ofertas_bot.models import Marketplace
from ofertas_bot.providers.amazon_gateway import AmazonGateway
from ofertas_bot.providers.amazon_request import AmazonSearchRequestBuilder
from ofertas_bot.providers.http import HttpResponse
from ofertas_bot.providers.shopee_gateway import ShopeeGateway
from ofertas_bot.providers.shopee_signed_request import ShopeeSignedRequestBuilder
from ofertas_bot.providers.transport import StaticHttpTransport

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_shopee_contract_fixture_maps_to_offers() -> None:
    response = HttpResponse(
        status_code=200,
        data=load_fixture("shopee_search_response.json"),
    )
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
        limit=2,
        timestamp=1700000000,
    )

    assert len(offers) == 2
    assert offers[0].marketplace == Marketplace.SHOPEE
    assert offers[0].title == "Kit Maquiagem Shopee Anonimizado"
    assert offers[0].price == 49.9
    assert offers[0].old_price == 89.9
    assert offers[0].is_prime_or_free_shipping is True


def test_amazon_contract_fixture_maps_to_offers() -> None:
    response = HttpResponse(
        status_code=200,
        data=load_fixture("amazon_search_response.json"),
    )
    gateway = AmazonGateway(
        request_builder=AmazonSearchRequestBuilder(
            partner_tag="tag-20",
            base_url="https://example.com",
        ),
        transport=StaticHttpTransport(response=response),
    )

    offers = gateway.execute_search(keyword="maquiagem", niche="maquiagem", limit=2)

    assert len(offers) == 2
    assert offers[0].marketplace == Marketplace.AMAZON
    assert offers[0].title == "Kit Maquiagem Amazon Anonimizado"
    assert offers[0].price == 79.9
    assert offers[0].old_price == 119.9
    assert offers[0].image_url == "https://example.com/images/amazon-001.jpg"
