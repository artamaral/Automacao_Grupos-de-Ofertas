from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.publication_manifest_cli import run
from ofertas_bot.storage.json_message_draft_store import JsonMessageDraftStore
from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueItem,
    MessageReviewRouting,
)
from ofertas_bot.storage.json_publication_manifest_store import JsonPublicationManifestStore


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


def test_publication_manifest_cli_creates_ready_manifest(tmp_path, capsys) -> None:
    approved_path = tmp_path / "approved_messages.json"
    manifest_path = tmp_path / "publication_manifest.json"
    draft = make_draft()
    JsonMessageDraftStore(path=approved_path).save((draft,))

    exit_code = run(
        [
            "--approved-messages-json",
            str(approved_path),
            "--target",
            "grupo-maquiagem",
            "--save-publication-manifest-json",
            str(manifest_path),
        ]
    )

    manifest = JsonPublicationManifestStore(path=manifest_path).load()
    output = capsys.readouterr().out
    assert exit_code == 0
    assert len(manifest) == 1
    assert manifest[0].draft == draft
    assert manifest[0].target == "grupo-maquiagem"
    assert manifest[0].status == "ready"
    assert "Nenhum envio" in output


def test_publication_manifest_cli_creates_manifest_from_review_queue(tmp_path) -> None:
    queue_path = tmp_path / "review_queue.json"
    manifest_path = tmp_path / "publication_manifest.json"
    draft = make_draft()
    JsonMessageReviewQueueStore(path=queue_path).save(
        (
            MessageReviewQueueItem(
                draft=draft,
                status="approved",
                routing=MessageReviewRouting(
                    group_slug="auto-e-moto-ofertas",
                    group_name="Auto e Moto Ofertas",
                    destination_kind="group",
                    destination_ref="grupo-auto-e-moto",
                    message_tone="pratico",
                ),
            ),
        )
    )

    exit_code = run(
        [
            "--queue-json",
            str(queue_path),
            "--save-publication-manifest-json",
            str(manifest_path),
        ]
    )

    manifest = JsonPublicationManifestStore(path=manifest_path).load()
    assert exit_code == 0
    assert len(manifest) == 1
    assert manifest[0].target == "grupo-auto-e-moto"
