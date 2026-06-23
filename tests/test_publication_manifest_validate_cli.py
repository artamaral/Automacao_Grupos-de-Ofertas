from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.publication_manifest_validate_cli import run
from ofertas_bot.storage.json_publication_manifest_store import (
    JsonPublicationManifestStore,
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


def test_publication_manifest_validate_cli_accepts_ready_manifest(tmp_path) -> None:
    manifest_path = tmp_path / "publication_manifest.json"
    manifest = create_publication_manifest(
        drafts=(make_draft(),),
        target="grupo-maquiagem",
        created_at="2026-01-01T00:00:00+00:00",
    )
    JsonPublicationManifestStore(path=manifest_path).save(manifest)

    exit_code = run(["--publication-manifest-json", str(manifest_path)])

    assert exit_code == 0


def test_publication_manifest_validate_cli_blocks_empty_manifest(tmp_path) -> None:
    manifest_path = tmp_path / "publication_manifest.json"
    JsonPublicationManifestStore(path=manifest_path).save(())

    exit_code = run(["--publication-manifest-json", str(manifest_path)])

    assert exit_code == 3
