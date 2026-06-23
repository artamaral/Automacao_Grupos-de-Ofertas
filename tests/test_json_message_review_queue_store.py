import pytest

from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueItem,
    MessageReviewQueueUpdateError,
    approve_review_queue_item,
    approved_review_drafts,
    create_pending_review_queue,
    reject_review_queue_item,
    summarize_review_queue,
)


def make_draft(title: str = "Produto teste") -> MessageDraft:
    offer = Offer(
        marketplace=Marketplace.AMAZON,
        title=title,
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


def test_create_pending_review_queue() -> None:
    draft = make_draft()

    items = create_pending_review_queue((draft,))

    assert items == (MessageReviewQueueItem(draft=draft),)


def test_json_message_review_queue_store_saves_and_loads_items(tmp_path) -> None:
    path = tmp_path / "queue.json"
    store = JsonMessageReviewQueueStore(path=path)
    item = MessageReviewQueueItem(
        draft=make_draft(),
        status="approved",
        reviewer="Arthur",
        notes="ok",
    )

    store.save((item,))

    assert store.load() == (item,)


def test_json_message_review_queue_store_returns_empty_when_missing(tmp_path) -> None:
    store = JsonMessageReviewQueueStore(path=tmp_path / "missing.json")

    assert store.load() == ()


def test_approved_review_drafts_returns_only_approved_items() -> None:
    approved_draft = make_draft("Produto aprovado")
    pending_draft = make_draft("Produto pendente")
    items = (
        MessageReviewQueueItem(draft=approved_draft, status="approved"),
        MessageReviewQueueItem(draft=pending_draft, status="pending"),
    )

    drafts = approved_review_drafts(items)

    assert drafts == (approved_draft,)


def test_summarize_review_queue_counts_statuses() -> None:
    items = (
        MessageReviewQueueItem(draft=make_draft("Pendente"), status="pending"),
        MessageReviewQueueItem(draft=make_draft("Aprovado"), status="approved"),
        MessageReviewQueueItem(draft=make_draft("Rejeitado"), status="rejected"),
        MessageReviewQueueItem(draft=make_draft("Pendente 2"), status="pending"),
    )

    summary = summarize_review_queue(items)

    assert summary == {
        "total": 4,
        "pending": 2,
        "approved": 1,
        "rejected": 1,
    }


def test_approve_review_queue_item_marks_item_as_approved() -> None:
    items = create_pending_review_queue((make_draft("Produto 1"), make_draft("Produto 2")))

    updated_items = approve_review_queue_item(
        items=items,
        item_number=2,
        reviewer=" Arthur ",
        notes=" aprovado ",
    )

    assert updated_items[0].status == "pending"
    assert updated_items[1].status == "approved"
    assert updated_items[1].reviewer == "Arthur"
    assert updated_items[1].notes == "aprovado"


def test_reject_review_queue_item_marks_item_as_rejected() -> None:
    items = create_pending_review_queue((make_draft(),))

    updated_items = reject_review_queue_item(
        items=items,
        item_number=1,
        reviewer="Arthur",
        notes="fora do grupo",
    )

    assert updated_items[0].status == "rejected"
    assert updated_items[0].reviewer == "Arthur"
    assert updated_items[0].notes == "fora do grupo"


def test_review_queue_item_update_rejects_out_of_range_item_number() -> None:
    items = create_pending_review_queue((make_draft(),))

    with pytest.raises(MessageReviewQueueUpdateError):
        approve_review_queue_item(
            items=items,
            item_number=2,
            reviewer="Arthur",
        )
