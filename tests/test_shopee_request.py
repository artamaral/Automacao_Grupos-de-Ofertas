import hashlib
import hmac

from ofertas_bot.providers.shopee_request import SHOPEE_SEARCH_PATH, ShopeeSearchRequestBuilder


def test_shopee_search_request_builder_creates_signed_request() -> None:
    builder = ShopeeSearchRequestBuilder(
        partner_id="123",
        secret_key="abc",
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
