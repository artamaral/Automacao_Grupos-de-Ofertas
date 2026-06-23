from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueItem,
    MessageReviewQueueStoreError,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lista a fila local de revisão")
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
        items = store.load()
    except MessageReviewQueueStoreError as error:
        return _print_list_error(error=error)

    if not items:
        print("INFO | Fila de revisão vazia.")
        print("INFO | Nenhum envio foi executado.")
        return 0

    for item_number, item in enumerate(items, start=1):
        print(_format_review_queue_item(item_number=item_number, item=item))

    print("INFO | Nenhum envio foi executado.")
    return 0


def _format_review_queue_item(item_number: int, item: MessageReviewQueueItem) -> str:
    offer = item.draft.offer
    reviewer = item.reviewer or "-"
    notes = item.notes or "-"
    return (
        f"ITEM | {item_number} | status={item.status} | "
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
