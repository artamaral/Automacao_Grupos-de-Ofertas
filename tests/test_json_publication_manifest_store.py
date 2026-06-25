import pytest

from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.storage.json_message_review_queue_store import (
    MessageReviewQueueItem,
    MessageReviewRouting,
)
from ofertas_bot.storage.json_publication_manifest_store import (
    JsonPublicationManifestStore,
    PublicationManifestItem,
    PublicationManifestStoreError,
    create_publication_manifest,
    create_publication_manifest_from_review_queue,
    validate_publication_manifest,
)


def make_draft() -> MessageDraft:
    offer = Offer(
        marketplace=Marketplace.MOCK,
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


def test_create_publication_manifest_marks_items_as_ready() -> None:
    draft = make_draft()

    manifest = create_publication_manifest(
        drafts=(draft,),
        target=" grupo-maquiagem ",
        created_at="2026-01-01T00:00:00+00:00",
    )

    assert manifest == (
        PublicationManifestItem(
            draft=draft,
            target="grupo-maquiagem",
            status="ready",
            created_at="2026-01-01T00:00:00+00:00",
            channel_adapter="whatsapp",
            max_messages_per_run=0,
            min_interval_seconds=0,
        ),
    )


def test_create_publication_manifest_requires_target() -> None:
    with pytest.raises(PublicationManifestStoreError):
        create_publication_manifest(
            drafts=(make_draft(),),
            target=" ",
            created_at="2026-01-01T00:00:00+00:00",
        )


def test_create_publication_manifest_from_review_queue_uses_routed_targets() -> None:
    draft = make_draft()
    queue_items = (
        MessageReviewQueueItem(
            draft=draft,
            status="approved",
            routing=MessageReviewRouting(
                group_slug="beleza-ofertas",
                group_name="Beleza Ofertas",
                destination_kind="group",
                destination_ref="grupo-beleza",
                message_tone="direto",
                max_messages_per_run=2,
                max_messages_per_hour=5,
                min_interval_seconds=45,
                quiet_periods=("22:00-08:00",),
            ),
        ),
    )

    manifest = create_publication_manifest_from_review_queue(
        items=queue_items,
        created_at="2026-01-01T00:00:00+00:00",
    )

    assert manifest == (
        PublicationManifestItem(
            draft=draft,
            target="grupo-beleza",
            status="ready",
            created_at="2026-01-01T00:00:00+00:00",
            channel_adapter="whatsapp",
            max_messages_per_run=2,
            max_messages_per_hour=5,
            min_interval_seconds=45,
            quiet_periods=("22:00-08:00",),
        ),
    )


def test_create_publication_manifest_from_review_queue_uses_fallback_target() -> None:
    draft = make_draft()
    queue_items = (
        MessageReviewQueueItem(
            draft=draft,
            status="approved",
        ),
    )

    manifest = create_publication_manifest_from_review_queue(
        items=queue_items,
        fallback_target="grupo-fallback",
        created_at="2026-01-01T00:00:00+00:00",
    )

    assert manifest[0].target == "grupo-fallback"
    assert manifest[0].channel_adapter == "whatsapp"


def test_validate_publication_manifest_accepts_ready_manifest() -> None:
    manifest = create_publication_manifest(
        drafts=(make_draft(),),
        target="grupo-maquiagem",
        created_at="2026-01-01T00:00:00+00:00",
    )

    assert validate_publication_manifest(manifest) == ()


def test_validate_publication_manifest_rejects_empty_manifest() -> None:
    assert validate_publication_manifest(()) == ("manifesto vazio",)


def test_json_publication_manifest_store_saves_and_loads_items(tmp_path) -> None:
    path = tmp_path / "publication_manifest.json"
    store = JsonPublicationManifestStore(path=path)
    item = PublicationManifestItem(
        draft=make_draft(),
        target="grupo-maquiagem",
        status="ready",
        created_at="2026-01-01T00:00:00+00:00",
    )

    store.save((item,))

    assert store.load() == (item,)
