import pytest

from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.storage.json_message_draft_store import (
    JsonMessageDraftStore,
    MessageDraftStoreError,
)


def make_draft() -> MessageDraft:
    offer = Offer(
        marketplace=Marketplace.AMAZON,
        title="Produto teste",
        url="https://example.com/produto",
        image_url=None,
        price=10,
        old_price=20,
        commission_rate=0.05,
        sales_count=100,
        rating=4.7,
        niche="teste",
    )
    return MessageDraft(
        offer=offer,
        text="Link de afiliado com comissão: https://example.com/produto",
    )


def test_json_message_draft_store_saves_and_loads_drafts(tmp_path) -> None:
    path = tmp_path / "drafts.json"
    store = JsonMessageDraftStore(path=path)
    draft = make_draft()

    store.save((draft,))

    assert store.load() == (draft,)


def test_json_message_draft_store_returns_empty_when_missing(tmp_path) -> None:
    store = JsonMessageDraftStore(path=tmp_path / "missing.json")

    assert store.load() == ()


def test_json_message_draft_store_rejects_invalid_json(tmp_path) -> None:
    path = tmp_path / "drafts.json"
    path.write_text("{", encoding="utf-8")
    store = JsonMessageDraftStore(path=path)

    with pytest.raises(MessageDraftStoreError):
        store.load()


def test_json_message_draft_store_rejects_non_list_payload(tmp_path) -> None:
    path = tmp_path / "drafts.json"
    path.write_text("{}", encoding="utf-8")
    store = JsonMessageDraftStore(path=path)

    with pytest.raises(MessageDraftStoreError):
        store.load()
