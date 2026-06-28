import json

import pytest

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.storage.json_offer_store import (
    JsonOfferStore,
    OfferStoreError,
    offer_from_json,
    offer_to_json,
)


def make_offer() -> Offer:
    return Offer(
        marketplace=Marketplace.SHOPEE,
        title="Kit Maquiagem",
        url="https://example.com/oferta",
        image_url="https://example.com/image.jpg",
        price=49.9,
        old_price=89.9,
        commission_rate=0.08,
        sales_count=1200,
        rating=4.8,
        niche="maquiagem",
        is_prime_or_free_shipping=True,
        shop_type_code=1,
        selected_at="2026-06-27T12:00:00+00:00",
        cooldown_until="2026-06-28T12:00:00+00:00",
        last_sent_at="2026-06-27T13:00:00+00:00",
    )


def test_offer_to_json_keeps_safe_serializable_fields() -> None:
    payload = offer_to_json(make_offer())

    assert payload == {
        "marketplace": "shopee",
        "title": "Kit Maquiagem",
        "url": "https://example.com/oferta",
        "image_url": "https://example.com/image.jpg",
        "price": 49.9,
        "old_price": 89.9,
        "commission_rate": 0.08,
        "sales_count": 1200,
        "rating": 4.8,
        "niche": "maquiagem",
        "item_id": None,
        "is_prime_or_free_shipping": True,
        "shop_type_code": 1,
        "selected_at": "2026-06-27T12:00:00+00:00",
        "cooldown_until": "2026-06-28T12:00:00+00:00",
        "last_sent_at": "2026-06-27T13:00:00+00:00",
    }


def test_offer_from_json_restores_offer() -> None:
    offer = offer_from_json(offer_to_json(make_offer()))

    assert offer == make_offer()


def test_json_offer_store_saves_and_loads_offers(tmp_path) -> None:
    path = tmp_path / "offers" / "normalized.json"
    store = JsonOfferStore(path=path)

    store.save([make_offer()])
    offers = store.load()

    assert offers == [make_offer()]
    assert json.loads(path.read_text(encoding="utf-8"))[0]["title"] == "Kit Maquiagem"


def test_json_offer_store_returns_empty_list_when_file_is_missing(tmp_path) -> None:
    store = JsonOfferStore(path=tmp_path / "missing.json")

    assert store.load() == []


def test_json_offer_store_rejects_invalid_json(tmp_path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("{", encoding="utf-8")
    store = JsonOfferStore(path=path)

    with pytest.raises(OfferStoreError, match="invalid"):
        store.load()


def test_json_offer_store_rejects_non_list_payload(tmp_path) -> None:
    path = tmp_path / "invalid-shape.json"
    path.write_text('{"title": "Oferta"}', encoding="utf-8")
    store = JsonOfferStore(path=path)

    with pytest.raises(OfferStoreError, match="list"):
        store.load()


def test_offer_from_json_rejects_invalid_item() -> None:
    with pytest.raises(OfferStoreError, match="invalid"):
        offer_from_json({"marketplace": "shopee"})
