from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.review_queue_export_cli import run
from ofertas_bot.storage.json_message_draft_store import JsonMessageDraftStore
from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueItem,
    MessageReviewRouting,
)


def make_draft(title: str) -> MessageDraft:
    offer = Offer(
        marketplace=Marketplace.MOCK,
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


def test_review_queue_export_cli_exports_only_approved_items(tmp_path, capsys) -> None:
    queue_path = tmp_path / "review_queue.json"
    output_json_path = tmp_path / "approved_messages.json"
    output_text_path = tmp_path / "approved_messages.txt"
    approved_draft = make_draft("Produto aprovado")
    rejected_draft = make_draft("Produto rejeitado")
    JsonMessageReviewQueueStore(path=queue_path).save(
        (
            MessageReviewQueueItem(draft=approved_draft, status="approved"),
            MessageReviewQueueItem(draft=rejected_draft, status="rejected"),
        )
    )

    exit_code = run(
        [
            "--queue-json",
            str(queue_path),
            "--save-approved-messages-json",
            str(output_json_path),
            "--save-approved-messages-text",
            str(output_text_path),
        ]
    )

    exported_drafts = JsonMessageDraftStore(path=output_json_path).load()
    output = capsys.readouterr().out
    text_output = output_text_path.read_text(encoding="utf-8-sig")
    assert exit_code == 0
    assert exported_drafts == (approved_draft,)
    assert "Produto aprovado" in text_output
    assert "Produto rejeitado" not in text_output
    assert "Nenhum envio" in output


def test_review_queue_export_cli_includes_group_routing_in_text(tmp_path) -> None:
    queue_path = tmp_path / "review_queue.json"
    output_text_path = tmp_path / "approved_messages.txt"
    approved_draft = make_draft("Produto aprovado")
    JsonMessageReviewQueueStore(path=queue_path).save(
        (
            MessageReviewQueueItem(
                draft=approved_draft,
                status="approved",
                routing=MessageReviewRouting(
                    group_slug="mae-e-bebe-ofertas",
                    group_name="Mae e Bebe Ofertas",
                    destination_kind="group",
                    destination_ref="grupo-mae-bebe",
                    message_tone="acolhedor",
                ),
            ),
        )
    )

    exit_code = run(
        [
            "--queue-json",
            str(queue_path),
            "--save-approved-messages-text",
            str(output_text_path),
        ]
    )

    text_output = output_text_path.read_text(encoding="utf-8-sig")
    assert exit_code == 0
    assert "Grupo: Mae e Bebe Ofertas" in text_output
    assert "Destino: group:grupo-mae-bebe" in text_output
    assert "Tom: acolhedor" in text_output


def test_review_queue_export_cli_exports_approved_items_by_group(tmp_path) -> None:
    queue_path = tmp_path / "review_queue.json"
    output_dir = tmp_path / "approved_by_group"
    beleza_draft = make_draft("Produto beleza")
    mae_bebe_draft = make_draft("Produto mae e bebe")
    JsonMessageReviewQueueStore(path=queue_path).save(
        (
            MessageReviewQueueItem(
                draft=beleza_draft,
                status="approved",
                routing=MessageReviewRouting(
                    group_slug="beleza-ofertas",
                    group_name="Beleza Ofertas",
                    destination_kind="group",
                    destination_ref="grupo-beleza",
                    message_tone="direto",
                ),
            ),
            MessageReviewQueueItem(
                draft=mae_bebe_draft,
                status="approved",
                routing=MessageReviewRouting(
                    group_slug="mae-e-bebe-ofertas",
                    group_name="Mae e Bebe Ofertas",
                    destination_kind="group",
                    destination_ref="grupo-mae-bebe",
                    message_tone="acolhedor",
                ),
            ),
        )
    )

    exit_code = run(
        [
            "--queue-json",
            str(queue_path),
            "--save-approved-messages-by-group-dir",
            str(output_dir),
        ]
    )

    beleza_json = JsonMessageDraftStore(path=output_dir / "beleza-ofertas.json").load()
    mae_bebe_json = JsonMessageDraftStore(path=output_dir / "mae-e-bebe-ofertas.json").load()
    beleza_text = (output_dir / "beleza-ofertas.txt").read_text(encoding="utf-8-sig")
    mae_bebe_text = (output_dir / "mae-e-bebe-ofertas.txt").read_text(encoding="utf-8-sig")
    assert exit_code == 0
    assert beleza_json == (beleza_draft,)
    assert mae_bebe_json == (mae_bebe_draft,)
    assert "Produto beleza" in beleza_text
    assert "Produto mae e bebe" in mae_bebe_text


def test_review_queue_export_cli_requires_output_path(tmp_path) -> None:
    queue_path = tmp_path / "review_queue.json"
    JsonMessageReviewQueueStore(path=queue_path).save(())

    exit_code = run(["--queue-json", str(queue_path)])

    assert exit_code == 3


def test_review_queue_export_cli_blocks_with_pending_item(tmp_path) -> None:
    queue_path = tmp_path / "review_queue.json"
    output_json_path = tmp_path / "approved_messages.json"
    JsonMessageReviewQueueStore(path=queue_path).save(
        (
            MessageReviewQueueItem(draft=make_draft("Produto aprovado"), status="approved"),
            MessageReviewQueueItem(draft=make_draft("Produto pendente"), status="pending"),
        )
    )

    exit_code = run(
        [
            "--queue-json",
            str(queue_path),
            "--save-approved-messages-json",
            str(output_json_path),
        ]
    )

    assert exit_code == 3
    assert not output_json_path.exists()
