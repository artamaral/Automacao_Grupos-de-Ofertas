from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.storage.json_selection_state_store import (
    JsonSelectionStateStore,
    merge_selection_state_into_offers,
    stamp_selected_offers,
    update_selection_state_from_selected_offers,
    update_selection_state_last_sent_at,
)


def _make_offer() -> Offer:
    return Offer(
        marketplace=Marketplace.SHOPEE,
        title="Oferta teste",
        url="https://example.com/oferta",
        image_url=None,
        price=10.0,
        old_price=None,
        commission_rate=0.1,
        sales_count=5,
        rating=5.0,
        niche="feminino",
        item_id=123,
    )


def test_selection_state_store_saves_and_loads_records(tmp_path) -> None:
    path = tmp_path / "selection_state.json"
    store = JsonSelectionStateStore(path=path)
    offer = _make_offer()
    stamped_offer = stamp_selected_offers(
        [offer],
        selected_at="2026-06-27T12:00:00+00:00",
        cooldown_until="2026-06-28T12:00:00+00:00",
    )[0]

    records = update_selection_state_from_selected_offers({}, [stamped_offer])
    records = update_selection_state_last_sent_at(
        records,
        drafts=(MessageDraft(offer=stamped_offer, text="msg"),),
        last_sent_at="2026-06-27T13:00:00+00:00",
    )
    store.save(records)

    loaded = store.load()

    assert loaded[offer.stable_key].selected_at == "2026-06-27T12:00:00+00:00"
    assert loaded[offer.stable_key].cooldown_until == "2026-06-28T12:00:00+00:00"
    assert loaded[offer.stable_key].last_sent_at == "2026-06-27T13:00:00+00:00"
    assert loaded[offer.stable_key].selection_count == 1
    assert loaded[offer.stable_key].sent_count == 1


def test_merge_selection_state_into_offers_restores_operational_fields(tmp_path) -> None:
    path = tmp_path / "selection_state.json"
    store = JsonSelectionStateStore(path=path)
    offer = _make_offer()
    stamped_offer = stamp_selected_offers(
        [offer],
        selected_at="2026-06-27T12:00:00+00:00",
        cooldown_until="2026-06-28T12:00:00+00:00",
    )[0]
    records = update_selection_state_from_selected_offers({}, [stamped_offer])
    store.save(records)

    merged = merge_selection_state_into_offers([offer], store.load())

    assert merged[0].selected_at == "2026-06-27T12:00:00+00:00"
    assert merged[0].cooldown_until == "2026-06-28T12:00:00+00:00"
    assert merged[0].last_sent_at is None


def test_selection_state_counters_accumulate_across_rounds() -> None:
    offer = _make_offer()
    first = stamp_selected_offers(
        [offer],
        selected_at="2026-06-27T12:00:00+00:00",
        cooldown_until="2026-06-28T12:00:00+00:00",
    )[0]
    records = update_selection_state_from_selected_offers({}, [first])
    second = stamp_selected_offers(
        [offer],
        selected_at="2026-06-29T12:00:00+00:00",
        cooldown_until="2026-06-30T12:00:00+00:00",
    )[0]
    records = update_selection_state_from_selected_offers(records, [second])
    records = update_selection_state_last_sent_at(
        records,
        drafts=(MessageDraft(offer=second, text="msg"),),
        last_sent_at="2026-06-29T13:00:00+00:00",
    )

    assert records[offer.stable_key].selection_count == 2
    assert records[offer.stable_key].sent_count == 1
