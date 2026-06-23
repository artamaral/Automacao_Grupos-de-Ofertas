from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.review_queue_export_cli import run
from ofertas_bot.storage.json_message_draft_store import JsonMessageDraftStore
from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueItem,
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
    pending_draft = make_draft("Produto pendente")
    JsonMessageReviewQueueStore(path=queue_path).save(
        (
            MessageReviewQueueItem(draft=approved_draft, status="approved"),
            MessageReviewQueueItem(draft=pending_draft, status="pending"),
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
    assert exit_code == 0
    assert exported_drafts == (approved_draft,)
    assert "Produto aprovado" in output_text_path.read_text(encoding="utf-8-sig")
    assert "Produto pendente" not in output_text_path.read_text(encoding="utf-8-sig")
    assert "Nenhum envio" in output


def test_review_queue_export_cli_requires_output_path(tmp_path) -> None:
    queue_path = tmp_path / "review_queue.json"
    JsonMessageReviewQueueStore(path=queue_path).save(())

    exit_code = run(["--queue-json", str(queue_path)])

    assert exit_code == 3
