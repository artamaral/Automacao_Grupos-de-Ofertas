from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.review_queue_summary_cli import run
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
    assert "Roteadas: 0" in output
    assert "Sem rota: 3" in output
    assert "Nenhum envio" in output


def test_review_queue_summary_cli_prints_group_breakdown(tmp_path, capsys) -> None:
    queue_path = tmp_path / "review_queue.json"
    JsonMessageReviewQueueStore(path=queue_path).save(
        (
            MessageReviewQueueItem(
                draft=make_draft("Beleza"),
                status="pending",
                routing=MessageReviewRouting(
                    group_slug="beleza-ofertas",
                    group_name="Beleza Ofertas",
                    destination_kind="group",
                    destination_ref="grupo-beleza",
                    message_tone="direto",
                ),
            ),
            MessageReviewQueueItem(
                draft=make_draft("Auto"),
                status="approved",
                routing=MessageReviewRouting(
                    group_slug="auto-e-moto-ofertas",
                    group_name="Auto e Moto Ofertas",
                    destination_kind="group",
                    destination_ref="grupo-auto",
                    message_tone="direto",
                ),
            ),
        )
    )

    exit_code = run(["--queue-json", str(queue_path), "--by-group"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "group=auto-e-moto-ofertas total=1 pending=0 approved=1 rejected=0" in output
    assert "group=beleza-ofertas total=1 pending=1 approved=0 rejected=0" in output
