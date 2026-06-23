from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.review_queue_summary_cli import run
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


def test_review_queue_summary_cli_prints_status_counts(tmp_path, capsys) -> None:
    queue_path = tmp_path / "review_queue.json"
    JsonMessageReviewQueueStore(path=queue_path).save(
        (
            MessageReviewQueueItem(draft=make_draft("Pendente"), status="pending"),
            MessageReviewQueueItem(draft=make_draft("Aprovado"), status="approved"),
            MessageReviewQueueItem(draft=make_draft("Rejeitado"), status="rejected"),
        )
    )

    exit_code = run(["--queue-json", str(queue_path)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Total: 3" in output
    assert "Pendentes: 1" in output
    assert "Aprovadas: 1" in output
    assert "Rejeitadas: 1" in output
    assert "Nenhum envio" in output
