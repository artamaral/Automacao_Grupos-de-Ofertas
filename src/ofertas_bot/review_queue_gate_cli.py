from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueStoreError,
    summarize_review_queue,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida o gate local de aprovação")
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
        summary = summarize_review_queue(store.load())
    except MessageReviewQueueStoreError as error:
        return _print_gate_error(error=error)

    print(f"INFO | Total: {summary['total']}")
    print(f"INFO | Pendentes: {summary['pending']}")
    print(f"INFO | Aprovadas: {summary['approved']}")
    print(f"INFO | Rejeitadas: {summary['rejected']}")

    if summary["pending"] > 0:
        print("ERRO | Gate bloqueado: ainda existem itens pendentes.", file=sys.stderr)
        print("AÇÃO | Aprove ou rejeite todos os itens antes de seguir.", file=sys.stderr)
        return 3

    if summary["approved"] == 0:
        print("ERRO | Gate bloqueado: nenhuma mensagem aprovada.", file=sys.stderr)
        print("AÇÃO | Aprove ao menos uma mensagem antes de seguir.", file=sys.stderr)
        return 3

    print("INFO | Gate aprovado para exportação/publicação futura controlada.")
    print("INFO | Nenhum envio foi executado.")
    return 0


def _print_gate_error(error: Exception) -> int:
    print("ERRO | Não foi possível validar o gate de aprovação", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminho e formato da fila.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
