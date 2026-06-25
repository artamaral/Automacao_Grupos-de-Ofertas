from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueItem,
    MessageReviewQueueStoreError,
    filter_review_queue_items,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lista a fila local de revisão")
    parser.add_argument(
        "--group",
        default=None,
        help="Slug opcional do grupo para filtrar a fila",
    )
    parser.add_argument(
        "--queue-json",
        required=True,
        help="Caminho do arquivo local review_queue.json",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = JsonMessageReviewQueueStore(path=Path(args.queue_json))

    try:
        items = filter_review_queue_items(store.load(), group_slug=args.group)
    except MessageReviewQueueStoreError as error:
        return _print_list_error(error=error)

    if not items:
        print("INFO | Fila de revisão vazia.")
        print("INFO | Nenhum envio foi executado.")
        return 0

    if args.group:
        print(f"INFO | group={args.group.strip().lower()}")

    for item_number, item in enumerate(items, start=1):
        print(_format_review_queue_item(item_number=item_number, item=item))

    print("INFO | Nenhum envio foi executado.")
    return 0


def _format_review_queue_item(item_number: int, item: MessageReviewQueueItem) -> str:
    offer = item.draft.offer
    reviewer = item.reviewer or "-"
    notes = item.notes or "-"
    routing = item.routing
    group_slug = routing.group_slug if routing is not None else "-"
    destination_ref = routing.destination_ref if routing is not None else "-"
    destination_kind = routing.destination_kind if routing is not None else "-"
    return (
        f"ITEM | {item_number} | status={item.status} | "
        f"group={group_slug} | destination_kind={destination_kind} | "
        f"destination_ref={destination_ref} | "
        f"marketplace={offer.marketplace.value} | niche={offer.niche} | "
        f"price=R$ {offer.price:.2f} | title={offer.title} | "
        f"reviewer={reviewer} | notes={notes}"
    )


def _print_list_error(error: Exception) -> int:
    print("ERRO | Não foi possível listar a fila de revisão", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminho e formato da fila.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
