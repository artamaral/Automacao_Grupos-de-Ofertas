import pytest

from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.storage.json_publication_manifest_store import (
    JsonPublicationManifestStore,
    PublicationManifestItem,
    PublicationManifestStoreError,
    create_publication_manifest,
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
        ),
    )


def test_create_publication_manifest_requires_target() -> None:
    with pytest.raises(PublicationManifestStoreError):
        create_publication_manifest(
            drafts=(make_draft(),),
            target=" ",
            created_at="2026-01-01T00:00:00+00:00",
        )


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
