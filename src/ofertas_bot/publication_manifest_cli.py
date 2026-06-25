from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from ofertas_bot.storage.json_message_draft_store import (
    JsonMessageDraftStore,
    MessageDraftStoreError,
)
from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueStoreError,
)
from ofertas_bot.storage.json_publication_manifest_store import (
    JsonPublicationManifestStore,
    PublicationManifestStoreError,
    PublicationManifestStoreWriteError,
    create_publication_manifest,
    create_publication_manifest_from_review_queue,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera manifesto local de publicação futura")
    parser.add_argument(
        "--approved-messages-json",
        default=None,
        help="Caminho do arquivo local approved_messages.json",
    )
    parser.add_argument(
        "--queue-json",
        default=None,
        help="Caminho do arquivo local review_queue.json",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Alvo opt-in planejado para publicação futura controlada",
    )
    parser.add_argument(
        "--save-publication-manifest-json",
        required=True,
        help="Caminho local para salvar o manifesto",
    )
    parser.add_argument(
        "--adapter-kind",
        choices=("console", "whatsapp", "telegram"),
        default="whatsapp",
        help="Canal planejado para os itens do manifesto",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.queue_json and not args.approved_messages_json:
        return _print_manifest_input_error()

    try:
        if args.queue_json:
            queue_items = JsonMessageReviewQueueStore(path=Path(args.queue_json)).load()
            manifest = create_publication_manifest_from_review_queue(
                items=queue_items,
                fallback_target=args.target,
                fallback_channel_adapter=args.adapter_kind,
                created_at=_utc_now_iso(),
            )
        else:
            drafts = JsonMessageDraftStore(path=Path(args.approved_messages_json)).load()
            manifest = create_publication_manifest(
                drafts=drafts,
                target=str(args.target),
                created_at=_utc_now_iso(),
                channel_adapter=args.adapter_kind,
            )
        JsonPublicationManifestStore(
            path=Path(args.save_publication_manifest_json)
        ).save(manifest)
    except (
        MessageDraftStoreError,
        MessageReviewQueueStoreError,
        PublicationManifestStoreError,
        PublicationManifestStoreWriteError,
    ) as error:
        return _print_manifest_error(error=error)

    print(
        "INFO | Manifesto local de publicação futura salvo em "
        f"{args.save_publication_manifest_json}"
    )
    print(f"INFO | Total de itens prontos: {len(manifest)}")
    print("INFO | Nenhum envio foi executado.")
    return 0


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _print_manifest_error(error: Exception) -> int:
    print("ERRO | Não foi possível gerar o manifesto local", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminhos, alvo e formato do arquivo aprovado.", file=sys.stderr)
    return 3


def _print_manifest_input_error() -> int:
    print("ERRO | Nenhuma fonte de manifesto informada", file=sys.stderr)
    print(
        "AÃ‡ÃƒO | Use --queue-json ou --approved-messages-json para gerar o manifesto.",
        file=sys.stderr,
    )
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
