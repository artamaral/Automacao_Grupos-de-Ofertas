from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.publication_manifest_cli import run
from ofertas_bot.storage.json_message_draft_store import JsonMessageDraftStore
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
