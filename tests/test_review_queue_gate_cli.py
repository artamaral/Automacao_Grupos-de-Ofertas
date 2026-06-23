from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.review_queue_gate_cli import run
from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueItem,
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


def test_review_queue_gate_cli_passes_with_approved_item(tmp_path) -> None:
    queue_path = tmp_path / "review_queue.json"
    JsonMessageReviewQueueStore(path=queue_path).save(
        (MessageReviewQueueItem(draft=make_draft(), status="approved"),)
    )

    exit_code = run(["--queue-json", str(queue_path)])

    assert exit_code == 0


def test_review_queue_gate_cli_blocks_with_pending_item(tmp_path) -> None:
    queue_path = tmp_path / "review_queue.json"
    JsonMessageReviewQueueStore(path=queue_path).save(
        (MessageReviewQueueItem(draft=make_draft(), status="pending"),)
    )

    exit_code = run(["--queue-json", str(queue_path)])

    assert exit_code == 3
