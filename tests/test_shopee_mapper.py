from ofertas_bot.models import Marketplace
from ofertas_bot.providers.shopee_mapper import ShopeeOfferMapper


def test_shopee_mapper_normalizes_item_payload() -> None:
    item = {
        "title": " Kit Maquiagem ",
        "url": " https://example.com/shopee-item ",
        "price": "49.90",
        "old_price": "89.90",
        "image_url": "https://example.com/image.jpg",
        "commission_rate": "0.08",
        "sales_count": "1200",
        "rating": "4.8",
        "is_free_shipping": True,
    }

    offer = ShopeeOfferMapper().map_item(item=item, niche="maquiagem")

    assert offer.marketplace == Marketplace.SHOPEE
    assert offer.title == "Kit Maquiagem"
    assert offer.url == "https://example.com/shopee-item"
    assert offer.price == 49.90
    assert offer.old_price == 89.90
    assert offer.commission_rate == 0.08
    assert offer.sales_count == 1200
    assert offer.rating == 4.8
    assert offer.niche == "maquiagem"
    assert offer.is_prime_or_free_shipping is True
