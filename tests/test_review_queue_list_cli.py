from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.review_queue_list_cli import run
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


def test_review_queue_list_cli_prints_items(tmp_path, capsys) -> None:
    queue_path = tmp_path / "review_queue.json"
    JsonMessageReviewQueueStore(path=queue_path).save(
        (
            MessageReviewQueueItem(draft=make_draft("Produto pendente"), status="pending"),
            MessageReviewQueueItem(
                draft=make_draft("Produto aprovado"),
                status="approved",
                reviewer="Arthur",
                notes="ok",
                routing=MessageReviewRouting(
                    group_slug="beleza-ofertas",
                    group_name="Beleza Ofertas",
                    destination_kind="group",
                    destination_ref="grupo-beleza",
                    message_tone="consultivo",
                ),
            ),
        )
    )

    exit_code = run(["--queue-json", str(queue_path)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "ITEM | 1 | status=pending" in output
    assert "ITEM | 2 | status=approved" in output
    assert "Produto pendente" in output
    assert "Produto aprovado" in output
    assert "reviewer=Arthur" in output
    assert "group=beleza-ofertas" in output
    assert "destination_ref=grupo-beleza" in output
    assert "Nenhum envio" in output


def test_review_queue_list_cli_handles_empty_queue(tmp_path, capsys) -> None:
    queue_path = tmp_path / "review_queue.json"
    JsonMessageReviewQueueStore(path=queue_path).save(())

    exit_code = run(["--queue-json", str(queue_path)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Fila de revisão vazia" in output
    assert "Nenhum envio" in output
