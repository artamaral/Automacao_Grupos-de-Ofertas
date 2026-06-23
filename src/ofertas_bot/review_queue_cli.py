from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueStoreError,
    MessageReviewQueueStoreWriteError,
    MessageReviewQueueUpdateError,
    approve_review_queue_item,
    reject_review_queue_item,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Atualiza a fila local de revisão")
    parser.add_argument(
        "--queue-json",
        required=True,
        help="Caminho do arquivo local review_queue.json",
    )
    parser.add_argument(
        "--item",
        required=True,
        type=int,
        help="Número do item na fila, começando em 1",
    )
    parser.add_argument(
        "--status",
        required=True,
        choices=["approved", "rejected"],
        help="Decisão humana para o item",
    )
    parser.add_argument(
        "--reviewer",
        required=True,
        help="Nome de quem revisou",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="Observação opcional da revisão",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = JsonMessageReviewQueueStore(path=Path(args.queue_json))

    try:
        items = store.load()
        if args.status == "approved":
            updated_items = approve_review_queue_item(
                items=items,
                item_number=args.item,
                reviewer=args.reviewer,
                notes=args.notes,
            )
        else:
            updated_items = reject_review_queue_item(
                items=items,
                item_number=args.item,
                reviewer=args.reviewer,
                notes=args.notes,
            )
        store.save(updated_items)
    except (
        MessageReviewQueueStoreError,
        MessageReviewQueueStoreWriteError,
        MessageReviewQueueUpdateError,
    ) as error:
        return _print_review_queue_error(error=error)

    print(
        f"INFO | Item {args.item} da fila marcado como {args.status} "
        f"por {args.reviewer.strip()}"
    )
    print("INFO | Nenhum envio foi executado.")
    return 0


def _print_review_queue_error(error: Exception) -> int:
    print("ERRO | Não foi possível atualizar a fila de revisão", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminho, item e formato do arquivo.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
