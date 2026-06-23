from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ofertas_bot.storage.json_message_draft_store import (
    JsonMessageDraftStore,
    MessageDraftStoreWriteError,
    format_message_drafts_for_review,
)
from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueStoreError,
    approved_review_drafts,
)

REVIEW_TEXT_ENCODING = "utf-8-sig"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exporta mensagens aprovadas da fila")
    parser.add_argument(
        "--queue-json",
        required=True,
        help="Caminho do arquivo local review_queue.json",
    )
    parser.add_argument(
        "--save-approved-messages-json",
        default=None,
        help="Caminho local para salvar mensagens aprovadas em JSON",
    )
    parser.add_argument(
        "--save-approved-messages-text",
        default=None,
        help="Caminho local para salvar mensagens aprovadas em texto",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.save_approved_messages_json and not args.save_approved_messages_text:
        return _print_missing_output_error()

    queue_store = JsonMessageReviewQueueStore(path=Path(args.queue_json))

    try:
        approved_drafts = approved_review_drafts(queue_store.load())
        if args.save_approved_messages_json:
            JsonMessageDraftStore(path=Path(args.save_approved_messages_json)).save(
                approved_drafts
            )
            print(
                "INFO | Mensagens aprovadas exportadas em "
                f"{args.save_approved_messages_json}"
            )
        if args.save_approved_messages_text:
            save_path = Path(args.save_approved_messages_text)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(
                format_message_drafts_for_review(approved_drafts),
                encoding=REVIEW_TEXT_ENCODING,
            )
            print(f"INFO | Revisão aprovada salva em {save_path}")
    except (MessageReviewQueueStoreError, MessageDraftStoreWriteError, OSError) as error:
        return _print_export_error(error=error)

    print(f"INFO | Total de mensagens aprovadas exportadas: {len(approved_drafts)}")
    print("INFO | Nenhum envio foi executado.")
    return 0


def _print_missing_output_error() -> int:
    print("ERRO | Nenhum destino de exportação informado", file=sys.stderr)
    print(
        "AÇÃO | Use --save-approved-messages-json e/ou --save-approved-messages-text.",
        file=sys.stderr,
    )
    return 3


def _print_export_error(error: Exception) -> int:
    print("ERRO | Não foi possível exportar mensagens aprovadas", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminhos e formato da fila.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
