from ofertas_bot.providers.endpoints import (
    AMAZON_DEFAULT_BASE_URL,
    AMAZON_SEARCH_PATH,
    SHOPEE_DEFAULT_BASE_URL,
    SHOPEE_GRAPHQL_URL,
    SHOPEE_SEARCH_PATH,
)


def test_shopee_public_endpoints_are_available() -> None:
    assert SHOPEE_DEFAULT_BASE_URL == "https://example.com"
    assert SHOPEE_SEARCH_PATH == "/api/v2/product/search_item"
    assert SHOPEE_GRAPHQL_URL == "https://open-api.affiliate.shopee.com.br/graphql"


def test_amazon_public_endpoints_are_available() -> None:
    assert AMAZON_DEFAULT_BASE_URL == "https://example.com"
    assert AMAZON_SEARCH_PATH == "/paapi5/searchitems"
