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
    resolve_review_queue_item_number,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Atualiza a fila local de revisão")
    parser.add_argument(
        "--group",
        default=None,
        help="Slug opcional do grupo para resolver o item dentro do grupo",
    )
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
                group_slug=args.group,
            )
        else:
            updated_items = reject_review_queue_item(
                items=items,
                item_number=args.item,
                reviewer=args.reviewer,
                notes=args.notes,
                group_slug=args.group,
            )
        store.save(updated_items)
        resolved_item_number = resolve_review_queue_item_number(
            items=updated_items,
            item_number=args.item,
            group_slug=args.group,
        )
    except (
        MessageReviewQueueStoreError,
        MessageReviewQueueStoreWriteError,
        MessageReviewQueueUpdateError,
    ) as error:
        return _print_review_queue_error(error=error)

    updated_item = updated_items[resolved_item_number - 1]
    routing_suffix = ""
    if updated_item.routing is not None:
        routing_suffix = (
            f" | group={updated_item.routing.group_slug}"
            f" | destination_ref={updated_item.routing.destination_ref or '-'}"
        )
    print(
        f"INFO | Item {args.item} da fila marcado como {args.status} "
        f"por {args.reviewer.strip()}{routing_suffix}"
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
