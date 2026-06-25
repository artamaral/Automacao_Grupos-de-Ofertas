from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueStoreError,
    summarize_review_queue,
    summarize_review_queue_by_group,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resume a fila local de revisão")
    parser.add_argument(
        "--by-group",
        action="store_true",
        default=False,
        help="Mostra resumo adicional por grupo",
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
        items = store.load()
        summary = summarize_review_queue(items)
    except MessageReviewQueueStoreError as error:
        return _print_summary_error(error=error)

    print(f"INFO | Total: {summary['total']}")
    print(f"INFO | Pendentes: {summary['pending']}")
    print(f"INFO | Aprovadas: {summary['approved']}")
    print(f"INFO | Rejeitadas: {summary['rejected']}")
    print(f"INFO | Roteadas: {summary['routed']}")
    print(f"INFO | Sem rota: {summary['unrouted']}")
    if args.by_group:
        for group_summary in summarize_review_queue_by_group(items):
            print(
                "INFO | group="
                f"{group_summary['group_slug']} total={group_summary['total']} "
                f"pending={group_summary['pending']} approved={group_summary['approved']} "
                f"rejected={group_summary['rejected']}"
            )
    print("INFO | Nenhum envio foi executado.")
    return 0


def _print_summary_error(error: Exception) -> int:
    print("ERRO | Não foi possível resumir a fila de revisão", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminho e formato da fila.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
