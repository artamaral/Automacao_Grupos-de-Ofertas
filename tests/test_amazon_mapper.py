import pytest

from ofertas_bot.models import Marketplace
from ofertas_bot.providers.amazon_mapper import AmazonOfferMapper
from ofertas_bot.providers.mapper import OfferMappingError


def test_amazon_offer_mapper_maps_item_to_offer() -> None:
    mapper = AmazonOfferMapper()
    item = {
        "ItemInfo": {"Title": {"DisplayValue": "Kit Maquiagem Amazon"}},
        "DetailPageURL": "https://example.com/amazon-1",
        "Images": {"Primary": {"Medium": {"URL": "https://example.com/image.jpg"}}},
        "Offers": {
            "Listings": [
                {
                    "Price": {"Amount": 79.9},
                    "SavingBasis": {"Amount": 119.9},
                }
            ]
        },
    }

    offer = mapper.map_item(item=item, niche="maquiagem")

    assert offer.marketplace == Marketplace.AMAZON
    assert offer.title == "Kit Maquiagem Amazon"
    assert offer.url == "https://example.com/amazon-1"
    assert offer.image_url == "https://example.com/image.jpg"
    assert offer.price == 79.9
    assert offer.old_price == 119.9
    assert offer.discount_percent == 33.36
    assert offer.commission_rate == 0.0
    assert offer.sales_count == 0
    assert offer.rating is None
    assert offer.niche == "maquiagem"


def test_amazon_offer_mapper_rejects_item_without_title() -> None:
    mapper = AmazonOfferMapper()
    item = {
        "DetailPageURL": "https://example.com/amazon-1",
        "Offers": {"Listings": [{"Price": {"Amount": 79.9}}]},
    }

    with pytest.raises(OfferMappingError, match="title"):
        mapper.map_item(item=item, niche="maquiagem")


def test_amazon_offer_mapper_rejects_item_without_url() -> None:
    mapper = AmazonOfferMapper()
    item = {
        "ItemInfo": {"Title": {"DisplayValue": "Kit Maquiagem Amazon"}},
        "Offers": {"Listings": [{"Price": {"Amount": 79.9}}]},
    }

    with pytest.raises(OfferMappingError, match="url"):
        mapper.map_item(item=item, niche="maquiagem")


def test_amazon_offer_mapper_rejects_item_without_price() -> None:
    mapper = AmazonOfferMapper()
    item = {
        "ItemInfo": {"Title": {"DisplayValue": "Kit Maquiagem Amazon"}},
        "DetailPageURL": "https://example.com/amazon-1",
        "Offers": {"Listings": []},
    }

    with pytest.raises(OfferMappingError, match="price"):
        mapper.map_item(item=item, niche="maquiagem")
