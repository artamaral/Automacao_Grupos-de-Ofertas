from datetime import UTC, datetime

import pytest

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.storage.json_offer_history_store import (
    JsonOfferHistoryStore,
    OfferHistoryEntry,
    OfferHistoryStoreError,
)


def _make_offer(title: str = "Produto teste", niche: str = "mae e bebe") -> Offer:
    return Offer(
        marketplace=Marketplace.SHOPEE,
        title=title,
        url="https://s.shopee.com.br/item-1?utm_source=afiliado",
        image_url=None,
        price=10.0,
        old_price=20.0,
        commission_rate=0.1,
        sales_count=10,
        rating=4.8,
        niche=niche,
    )


def test_offer_stable_key_ignores_query_string() -> None:
    first = _make_offer()
    second = Offer(
        marketplace=Marketplace.SHOPEE,
        title="Produto teste",
        url="https://s.shopee.com.br/item-1?utm_source=outra&utm_campaign=x",
        image_url=None,
        price=10.0,
        old_price=20.0,
        commission_rate=0.1,
        sales_count=10,
        rating=4.8,
        niche="mae e bebe",
    )

    assert first.stable_key == second.stable_key


def test_json_offer_history_store_saves_and_loads(tmp_path) -> None:
    path = tmp_path / "offer-history.json"
    now = datetime(2026, 6, 26, 10, 0, tzinfo=UTC)
    entry = OfferHistoryEntry(
        offer_key="abc",
        marketplace=Marketplace.SHOPEE,
        title="Produto teste",
        url="https://example.com/item",
        first_seen_at=now,
        last_seen_at=now,
        last_published_at=None,
        publish_count=0,
        niches=("mae e bebe",),
        group_slugs=(),
    )
    store = JsonOfferHistoryStore(path=path)

    store.save({"abc": entry})

    assert store.load() == {"abc": entry}


def test_json_offer_history_store_returns_empty_when_missing(tmp_path) -> None:
    store = JsonOfferHistoryStore(path=tmp_path / "missing.json")

    assert store.load() == {}


def test_json_offer_history_store_touch_offers_creates_and_updates_entry(tmp_path) -> None:
    store = JsonOfferHistoryStore(path=tmp_path / "offer-history.json")
    first_seen = datetime(2026, 6, 26, 10, 0, tzinfo=UTC)
    last_seen = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)
    offer = _make_offer()

    history = store.touch_offers(offers=[offer], seen_at=first_seen)
    updated_history = store.touch_offers(
        offers=[_make_offer(niche="infantil")],
        seen_at=last_seen,
    )

    entry = history[offer.stable_key]
    updated_entry = updated_history[offer.stable_key]
    assert entry.first_seen_at == first_seen
    assert updated_entry.first_seen_at == first_seen
    assert updated_entry.last_seen_at == last_seen
    assert updated_entry.niches == ("mae e bebe", "infantil")


def test_json_offer_history_store_mark_offer_published_tracks_count_and_group(tmp_path) -> None:
    store = JsonOfferHistoryStore(path=tmp_path / "offer-history.json")
    published_at = datetime(2026, 6, 26, 15, 0, tzinfo=UTC)
    offer = _make_offer()

    entry = store.mark_offer_published(
        offer=offer,
        published_at=published_at,
        group_slug="grupo-mae-e-bebe",
    )

    assert entry.publish_count == 1
    assert entry.last_published_at == published_at
    assert entry.group_slugs == ("grupo-mae-e-bebe",)
    assert store.load()[offer.stable_key] == entry


def test_json_offer_history_store_rejects_invalid_json(tmp_path) -> None:
    path = tmp_path / "offer-history.json"
    path.write_text("{invalid", encoding="utf-8")
    store = JsonOfferHistoryStore(path=path)

    with pytest.raises(OfferHistoryStoreError, match="invalid"):
        store.load()


def test_json_offer_history_store_rejects_non_object_json(tmp_path) -> None:
    path = tmp_path / "offer-history.json"
    path.write_text("[]", encoding="utf-8")
    store = JsonOfferHistoryStore(path=path)

    with pytest.raises(OfferHistoryStoreError, match="object"):
        store.load()
