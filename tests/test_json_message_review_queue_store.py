import pytest

from ofertas_bot.group_profiles import GroupDestination, GroupProfile, GroupProfileCatalog
from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueItem,
    MessageReviewQueueUpdateError,
    MessageReviewRouting,
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
    catalog = GroupProfileCatalog.from_iterable(
        (
            GroupProfile(
                slug="grupo-teste",
                name="Grupo Teste",
                allowed_niches=("teste",),
                allowed_marketplaces=(Marketplace.AMAZON,),
                message_tone="direto",
                destinations=(
                    GroupDestination(
                        destination_kind="group",
                        destination_ref="grupo-teste-destino",
                        channel_adapter="whatsapp",
                        max_messages_per_run=2,
                        max_messages_per_hour=5,
                        min_interval_seconds=45,
                        quiet_periods=("22:00-08:00",),
                    ),
                ),
            ),
        )
    )

    items = create_pending_review_queue((draft,), group_catalog=catalog)

    assert items == (
        MessageReviewQueueItem(
            draft=draft,
            routing=MessageReviewRouting(
                group_slug="grupo-teste",
                group_name="Grupo Teste",
                destination_kind="group",
                destination_ref="grupo-teste-destino",
                channel_adapter="whatsapp",
                message_tone="direto",
                max_messages_per_run=2,
                max_messages_per_hour=5,
                min_interval_seconds=45,
                quiet_periods=("22:00-08:00",),
            ),
        ),
    )


def test_create_pending_review_queue_expands_multiple_destinations() -> None:
    draft = make_draft()
    catalog = GroupProfileCatalog.from_iterable(
        (
            GroupProfile(
                slug="grupo-teste",
                name="Grupo Teste",
                allowed_niches=("teste",),
                allowed_marketplaces=(Marketplace.AMAZON,),
                message_tone="direto",
                destinations=(
                    GroupDestination(
                        destination_kind="group",
                        destination_ref="grupo-whatsapp",
                        channel_adapter="whatsapp",
                        max_messages_per_run=2,
                        max_messages_per_hour=5,
                        min_interval_seconds=45,
                        quiet_periods=("22:00-08:00",),
                    ),
                    GroupDestination(
                        destination_kind="channel",
                        destination_ref="canal-telegram",
                        channel_adapter="telegram",
                        max_messages_per_run=1,
                        max_messages_per_hour=3,
                        min_interval_seconds=60,
                        quiet_periods=("23:00-07:00",),
                    ),
                ),
            ),
        )
    )

    items = create_pending_review_queue((draft,), group_catalog=catalog)

    assert len(items) == 2
    assert items[0].routing is not None
    assert items[0].routing.destination_ref == "grupo-whatsapp"
    assert items[0].routing.channel_adapter == "whatsapp"
    assert items[0].routing.max_messages_per_run == 2
    assert items[0].routing.max_messages_per_hour == 5
    assert items[0].routing.min_interval_seconds == 45
    assert items[0].routing.quiet_periods == ("22:00-08:00",)
    assert items[1].routing is not None
    assert items[1].routing.destination_ref == "canal-telegram"
    assert items[1].routing.channel_adapter == "telegram"
    assert items[1].routing.max_messages_per_run == 1
    assert items[1].routing.max_messages_per_hour == 3
    assert items[1].routing.min_interval_seconds == 60
    assert items[1].routing.quiet_periods == ("23:00-07:00",)


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
        "routed": 0,
        "unrouted": 4,
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


def test_create_pending_review_queue_keeps_unrouted_item_when_no_group_matches() -> None:
    draft = make_draft()
    catalog = GroupProfileCatalog.from_iterable(
        (
            GroupProfile(
                slug="grupo-beleza",
                name="Grupo Beleza",
                allowed_niches=("beleza",),
                allowed_marketplaces=(Marketplace.MOCK,),
            ),
        )
    )

    items = create_pending_review_queue((draft,), group_catalog=catalog)

    assert items == (MessageReviewQueueItem(draft=draft),)


def test_review_queue_item_update_rejects_out_of_range_item_number() -> None:
    items = create_pending_review_queue((make_draft(),))

    with pytest.raises(MessageReviewQueueUpdateError):
        approve_review_queue_item(
            items=items,
            item_number=2,
            reviewer="Arthur",
        )
