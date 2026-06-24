import pytest

from ofertas_bot.models import Marketplace
from ofertas_bot.providers.mapper import ExternalOfferPayload, OfferMapper, OfferMappingError


def test_offer_mapper_normalizes_external_payload() -> None:
    payload = ExternalOfferPayload(
        marketplace=Marketplace.SHOPEE,
        title=" Produto teste ",
        url=" https://example.com/oferta ",
        price=49.90,
        old_price=89.90,
        niche=" maquiagem ",
        image_url="https://example.com/image.jpg",
        commission_rate=0.08,
        sales_count=100,
        rating=4.8,
        is_prime_or_free_shipping=True,
    )

    offer = OfferMapper().map_external_offer(payload)

    assert offer.marketplace == Marketplace.SHOPEE
    assert offer.title == "Produto teste"
    assert offer.url == "https://example.com/oferta"
    assert offer.price == 49.90
    assert offer.old_price == 89.90
    assert offer.niche == "maquiagem"
    assert offer.discount_percent == 44.49


def test_offer_mapper_rejects_invalid_payload() -> None:
    payload = ExternalOfferPayload(
        marketplace=Marketplace.AMAZON,
        title="",
        url="",
        price=0,
        old_price=None,
        niche="",
    )

    with pytest.raises(OfferMappingError) as error:
        OfferMapper().map_external_offer(payload)

    message = str(error.value)
    assert "title" in message
    assert "url" in message
    assert "price" in message
    assert "niche" in message


def test_offer_mapper_accepts_unknown_price_when_explicitly_allowed() -> None:
    payload = ExternalOfferPayload(
        marketplace=Marketplace.SHOPEE,
        title="Campanha Shopee",
        url="https://example.com/oferta",
        price=0,
        old_price=None,
        niche="maquiagem",
        allow_unknown_price=True,
    )

    offer = OfferMapper().map_external_offer(payload)

    assert offer.price == 0
    assert offer.title == "Campanha Shopee"
