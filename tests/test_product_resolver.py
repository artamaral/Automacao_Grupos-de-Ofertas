from ofertas_bot.product_resolver import ShopeeProductResolver, extract_shopee_product_ids
from ofertas_bot.settings import Settings


class FakeShopeeProvider:
    def __init__(self) -> None:
        self.request = None
        self.short_link_request = None

    def fetch_product_offer_raw_response(self, **kwargs):
        self.request = kwargs
        return {
            "data": {
                "productOfferV2": {
                    "nodes": [
                        {
                            "itemId": 456,
                            "shopId": 123,
                            "productName": "Produto teste",
                            "price": 80,
                            "priceDiscountRate": 20,
                            "imageUrl": "https://img.test/produto.jpg",
                            "productLink": "https://shopee.com.br/produto-i.123.456",
                            "sales": 321,
                            "ratingStar": 4.8,
                            "commissionRate": 12.5,
                        }
                    ]
                }
            }
        }

    def generate_short_link(self, *, origin_url, sub_ids):
        self.short_link_request = (origin_url, sub_ids)
        return "https://s.shopee.com.br/affiliate"


def test_extract_ids_from_standard_product_url() -> None:
    assert extract_shopee_product_ids(
        "https://shopee.com.br/Produto-qualquer-i.123.456?x=1"
    ) == (123, 456)


def test_resolver_builds_product_data_and_affiliate_url() -> None:
    provider = FakeShopeeProvider()
    resolver = ShopeeProductResolver(
        settings=Settings(shopee_tracking_id="offline"),
        provider=provider,  # type: ignore[arg-type]
    )

    product = resolver.resolve("https://shopee.com.br/Produto-qualquer-i.123.456")

    assert product.item_id == 456
    assert product.shop_id == 123
    assert product.price == 80
    assert product.old_price == 100
    assert product.discount_pct == 20
    assert product.affiliate_url == "https://s.shopee.com.br/affiliate"
    assert provider.request == {"limit": 1, "item_id": 456, "shop_id": 123}
    assert provider.short_link_request == (
        "https://shopee.com.br/produto-i.123.456",
        ["offline"],
    )


def test_short_url_can_use_injected_redirect_resolver() -> None:
    provider = FakeShopeeProvider()
    resolver = ShopeeProductResolver(
        settings=Settings(),
        provider=provider,  # type: ignore[arg-type]
        redirect_resolver=lambda _: "https://shopee.com.br/Produto-i.123.456",
    )

    assert resolver.resolve("https://s.shopee.com.br/abc").item_id == 456
