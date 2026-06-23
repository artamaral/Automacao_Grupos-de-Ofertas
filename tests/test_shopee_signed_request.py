import hashlib
import hmac

from ofertas_bot.providers.endpoints import SHOPEE_SEARCH_PATH
from ofertas_bot.providers.shopee_signed_request import ShopeeSignedRequestBuilder


def test_shopee_signed_request_builder_creates_http_request() -> None:
    builder = ShopeeSignedRequestBuilder(
        partner_id="123",
        api_credential="abc",
        base_url="https://example.com",
    )

    request = builder.build(keyword="maquiagem", limit=10, timestamp=1710000000)

    expected_base = f"123{SHOPEE_SEARCH_PATH}1710000000"
    expected_sign = hmac.new(
        b"abc",
        expected_base.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    assert request.method == "GET"
    assert request.url == f"https://example.com{SHOPEE_SEARCH_PATH}"
    assert request.params["partner_id"] == "123"
    assert request.params["timestamp"] == 1710000000
    assert request.params["sign"] == expected_sign
    assert request.params["keyword"] == "maquiagem"
    assert request.params["page_size"] == 10


def test_shopee_signed_request_builder_uses_configured_search_path() -> None:
    custom_path = "/custom/search"
    builder = ShopeeSignedRequestBuilder(
        partner_id="123",
        api_credential="abc",
        base_url="https://example.com",
        search_path=custom_path,
    )

    request = builder.build(keyword="maquiagem", limit=1, timestamp=1710000000)

    expected_base = f"123{custom_path}1710000000"
    expected_sign = hmac.new(
        b"abc",
        expected_base.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    assert request.url == "https://example.com/custom/search"
    assert request.params["sign"] == expected_sign
