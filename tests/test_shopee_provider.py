import pytest

from ofertas_bot.models import Marketplace
from ofertas_bot.providers.http import HttpResponse
from ofertas_bot.providers.shopee import ShopeeConfigurationError, ShopeeProvider
from ofertas_bot.providers.shopee_graphql import (
    SHOPEE_PRODUCT_OFFER_LIST_OPERATION,
    ShopeeGraphqlGateway,
    ShopeeGraphqlOfferMapper,
    ShopeeGraphqlSigner,
    ShopeeOfferListGraphqlRequestBuilder,
    ShopeeShortLinkGraphqlRequestBuilder,
)
from ofertas_bot.providers.transport import StaticHttpTransport
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


def test_shopee_provider_requires_configured_graphql_transport() -> None:
    settings = Settings(
        shopee_partner_id="configured",
        shopee_secret_key="configured",
    )
    provider = ShopeeProvider(settings=settings)

    with pytest.raises(NotImplementedError):
        provider.fetch(niche="maquiagem", limit=3)


def test_shopee_provider_fetch_uses_injected_transport() -> None:
    response = HttpResponse(
        status_code=200,
        data={
            "data": {
                "shopeeOfferV2": {
                    "nodes": [
                        {
                            "commissionRate": "0.08",
                            "imageUrl": "https://example.com/shopee-1.jpg",
                            "offerLink": "https://example.com/shopee-1",
                            "originalLink": "https://example.com/produto-1",
                            "offerName": "Kit Maquiagem",
                            "offerType": 1,
                            "collectionId": 123,
                            "periodStartTime": 1710000000,
                            "periodEndTime": 1710086400,
                        }
                    ],
                    "pageInfo": {
                        "page": 1,
                        "limit": 1,
                        "hasNextPage": False,
                    },
                }
            }
        },
    )
    transport = StaticHttpTransport(response=response)
    signer = ShopeeGraphqlSigner(credential="123", api_secret="abc")
    gateway = ShopeeGraphqlGateway(
        offer_list_builder=ShopeeOfferListGraphqlRequestBuilder(signer=signer),
        short_link_builder=ShopeeShortLinkGraphqlRequestBuilder(signer=signer),
        mapper=ShopeeGraphqlOfferMapper(marketplace=Marketplace.SHOPEE),
        transport=transport,
    )
    provider = ShopeeProvider(
        settings=Settings(shopee_partner_id="123", shopee_secret_key="abc"),
        graphql_gateway=gateway,
    )

    offers = provider.fetch(niche="maquiagem", limit=1)

    assert len(offers) == 1
    assert offers[0].marketplace == Marketplace.SHOPEE
    assert offers[0].title == "Kit Maquiagem"
    assert offers[0].price == 0
    assert transport.requests[0].body is not None
    assert transport.requests[0].body["variables"]["keyword"] == "maquiagem"


def test_shopee_provider_builds_search_request_after_configuration() -> None:
    settings = Settings(
        shopee_partner_id="123",
        shopee_secret_key="abc",
    )
    provider = ShopeeProvider(settings=settings)

    request = provider.build_search_request(
        keyword="maquiagem",
        limit=10,
        timestamp=1710000000,
    )

    assert request.method == "POST"
    assert request.body is not None
    assert request.body["operationName"] == "ShopeeOfferList"
    assert request.body["variables"]["keyword"] == "maquiagem"
    assert request.body["variables"]["limit"] == 10
    assert request.body["variables"]["page"] == 1
    assert request.headers["Authorization"].startswith("SHA256 Credential=123")


def test_shopee_provider_normalizes_response_items() -> None:
    provider = ShopeeProvider(settings=Settings())
    response_data = {
        "data": {
            "shopeeOfferV2": {
                "nodes": [
                    {
                        "commissionRate": "0.08",
                        "imageUrl": "https://example.com/shopee-1.jpg",
                        "offerLink": "https://example.com/shopee-1",
                        "originalLink": "https://example.com/produto-1",
                        "offerName": "Kit Maquiagem",
                        "offerType": 1,
                        "collectionId": 123,
                        "periodStartTime": 1710000000,
                        "periodEndTime": 1710086400,
                    },
                    {
                        "commissionRate": "0.05",
                        "imageUrl": "https://example.com/shopee-2.jpg",
                        "offerLink": "https://example.com/shopee-2",
                        "originalLink": "https://example.com/produto-2",
                        "offerName": "Oferta ignorada pelo limite",
                        "offerType": 2,
                        "categoryId": 456,
                        "periodStartTime": 1710000000,
                        "periodEndTime": 1710086400,
                    },
                ],
                "pageInfo": {"page": 1, "limit": 2, "hasNextPage": False},
            }
        }
    }

    offers = provider.normalize_response(response_data=response_data, niche="maquiagem", limit=1)

    assert len(offers) == 1
    assert offers[0].marketplace == Marketplace.SHOPEE
    assert offers[0].title == "Kit Maquiagem"
    assert offers[0].price == 0


def test_shopee_provider_rejects_invalid_items_shape() -> None:
    provider = ShopeeProvider(settings=Settings())

    with pytest.raises(ValueError, match="shopeeOfferV2"):
        provider.normalize_response(response_data={"data": {}}, niche="maquiagem", limit=1)


def test_shopee_provider_fetches_offer_search_with_explicit_shopee_offer_query() -> None:
    response = HttpResponse(
        status_code=200,
        data={"data": {"shopeeOfferV2": {"nodes": [], "pageInfo": {"page": 1, "limit": 1, "hasNextPage": False}}}},
    )
    transport = StaticHttpTransport(response=response)
    signer = ShopeeGraphqlSigner(credential="123", api_secret="abc")
    gateway = ShopeeGraphqlGateway(
        offer_list_builder=ShopeeOfferListGraphqlRequestBuilder(signer=signer),
        short_link_builder=ShopeeShortLinkGraphqlRequestBuilder(signer=signer),
        mapper=ShopeeGraphqlOfferMapper(marketplace=Marketplace.SHOPEE),
        transport=transport,
    )
    provider = ShopeeProvider(
        settings=Settings(shopee_partner_id="123", shopee_secret_key="abc"),
        graphql_gateway=gateway,
    )

    payload = provider.fetch_offer_search_raw_response("Mom & Baby", limit=5)

    assert payload["data"]["shopeeOfferV2"]["pageInfo"]["limit"] == 1
    assert transport.requests[0].body is not None
    assert transport.requests[0].body["operationName"] == "ShopeeOfferList"
    assert "shopeeOfferV2" in transport.requests[0].body["query"]
    assert transport.requests[0].body["variables"]["keyword"] == "Mom & Baby"


def test_shopee_provider_fetches_product_match_with_inline_query() -> None:
    response = HttpResponse(
        status_code=200,
        data={"data": {"productOfferV2": {"nodes": [], "pageInfo": {"page": 1, "limit": 3, "hasNextPage": False}}}},
    )
    transport = StaticHttpTransport(response=response)
    signer = ShopeeGraphqlSigner(credential="123", api_secret="abc")
    gateway = ShopeeGraphqlGateway(
        offer_list_builder=ShopeeOfferListGraphqlRequestBuilder(signer=signer),
        short_link_builder=ShopeeShortLinkGraphqlRequestBuilder(signer=signer),
        mapper=ShopeeGraphqlOfferMapper(marketplace=Marketplace.SHOPEE),
        transport=transport,
    )
    provider = ShopeeProvider(
        settings=Settings(shopee_partner_id="123", shopee_secret_key="abc"),
        graphql_gateway=gateway,
    )

    payload = provider.fetch_product_match_raw_response(match_id=100632, limit=3)

    assert payload["data"]["productOfferV2"]["pageInfo"]["limit"] == 3
    assert transport.requests[0].body is not None
    assert transport.requests[0].body["operationName"] == SHOPEE_PRODUCT_OFFER_LIST_OPERATION
    assert "productOfferV2" in transport.requests[0].body["query"]
    assert "matchId: 100632" in transport.requests[0].body["query"]
    assert transport.requests[0].body["variables"] == {}


def test_shopee_provider_fetches_product_match_with_optional_filters() -> None:
    response = HttpResponse(
        status_code=200,
        data={"data": {"productOfferV2": {"nodes": [], "pageInfo": {"page": 1, "limit": 50, "hasNextPage": False}}}},
    )
    transport = StaticHttpTransport(response=response)
    signer = ShopeeGraphqlSigner(credential="123", api_secret="abc")
    gateway = ShopeeGraphqlGateway(
        offer_list_builder=ShopeeOfferListGraphqlRequestBuilder(signer=signer),
        short_link_builder=ShopeeShortLinkGraphqlRequestBuilder(signer=signer),
        mapper=ShopeeGraphqlOfferMapper(marketplace=Marketplace.SHOPEE),
        transport=transport,
    )
    provider = ShopeeProvider(
        settings=Settings(shopee_partner_id="123", shopee_secret_key="abc"),
        graphql_gateway=gateway,
    )

    payload = provider.fetch_product_match_raw_response(
        match_id=None,
        limit=50,
        list_type=1,
        sort_type=2,
        is_key_seller=True,
    )

    assert payload["data"]["productOfferV2"]["pageInfo"]["limit"] == 50
    assert transport.requests[0].body is not None
    assert "listType: 1" in transport.requests[0].body["query"]
    assert "sortType: 2" in transport.requests[0].body["query"]
    assert "isKeySeller: true" in transport.requests[0].body["query"]
    assert "matchId:" not in transport.requests[0].body["query"]


def test_shopee_provider_fetches_product_offer_with_keyword_only() -> None:
    response = HttpResponse(
        status_code=200,
        data={"data": {"productOfferV2": {"nodes": [], "pageInfo": {"page": 1, "limit": 50, "hasNextPage": False}}}},
    )
    transport = StaticHttpTransport(response=response)
    signer = ShopeeGraphqlSigner(credential="123", api_secret="abc")
    gateway = ShopeeGraphqlGateway(
        offer_list_builder=ShopeeOfferListGraphqlRequestBuilder(signer=signer),
        short_link_builder=ShopeeShortLinkGraphqlRequestBuilder(signer=signer),
        mapper=ShopeeGraphqlOfferMapper(marketplace=Marketplace.SHOPEE),
        transport=transport,
    )
    provider = ShopeeProvider(
        settings=Settings(shopee_partner_id="123", shopee_secret_key="abc"),
        graphql_gateway=gateway,
    )

    payload = provider.fetch_product_offer_raw_response(
        limit=50,
        keyword="mae e bebe",
    )

    assert payload["data"]["productOfferV2"]["pageInfo"]["limit"] == 50
    assert transport.requests[0].body is not None
    assert 'keyword: "mae e bebe"' in transport.requests[0].body["query"]
    assert "listType:" not in transport.requests[0].body["query"]
