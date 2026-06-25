from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.review_queue_cli import run
from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueItem,
    MessageReviewRouting,
    create_pending_review_queue,
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


def test_review_queue_cli_marks_item_as_approved(tmp_path, capsys) -> None:
    queue_path = tmp_path / "review_queue.json"
    store = JsonMessageReviewQueueStore(path=queue_path)
    store.save(
        (
            MessageReviewQueueItem(
                draft=make_draft(),
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

    exit_code = run(
        [
            "--queue-json",
            str(queue_path),
            "--item",
            "1",
            "--status",
            "approved",
            "--reviewer",
            "Arthur",
            "--notes",
            "ok",
        ]
    )

    item = store.load()[0]
    output = capsys.readouterr().out
    assert exit_code == 0
    assert item.status == "approved"
    assert item.reviewer == "Arthur"
    assert item.notes == "ok"
    assert "group=auto-e-moto-ofertas" in output
    assert "Nenhum envio" in output


def test_review_queue_cli_rejects_out_of_range_item(tmp_path) -> None:
    queue_path = tmp_path / "review_queue.json"
    store = JsonMessageReviewQueueStore(path=queue_path)
    store.save(create_pending_review_queue((make_draft(),)))

    exit_code = run(
        [
            "--queue-json",
            str(queue_path),
            "--item",
            "2",
            "--status",
            "rejected",
            "--reviewer",
            "Arthur",
        ]
    )

    assert exit_code == 3
    assert store.load()[0].status == "pending"
