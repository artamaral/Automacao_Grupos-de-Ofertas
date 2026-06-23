from ofertas_bot.providers.endpoints import SHOPEE_DEFAULT_BASE_URL, SHOPEE_SEARCH_PATH


def test_shopee_public_endpoints_are_available() -> None:
    assert SHOPEE_DEFAULT_BASE_URL == "https://example.com"
    assert SHOPEE_SEARCH_PATH == "/api/v2/product/search_item"
