import hashlib
import hmac

from ofertas_bot.providers.shopee_auth import ShopeeAuthParams, ShopeeSigner


def test_shopee_signer_creates_expected_hmac_signature() -> None:
    params = ShopeeAuthParams(
        partner_id="123",
        secret_key="abc",
        path="/api/v2/product/search_item",
        timestamp=1710000000,
    )

    expected_base = "123/api/v2/product/search_item1710000000"
    expected = hmac.new(
        b"abc",
        expected_base.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    assert ShopeeSigner().sign(params) == expected
