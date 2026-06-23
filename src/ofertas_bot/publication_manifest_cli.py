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
from ofertas_bot.storage.json_publication_manifest_store import (
    JsonPublicationManifestStore,
    PublicationManifestStoreError,
    PublicationManifestStoreWriteError,
    create_publication_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera manifesto local de publicação futura")
    parser.add_argument(
        "--approved-messages-json",
        required=True,
        help="Caminho do arquivo local approved_messages.json",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Alvo opt-in planejado para publicação futura controlada",
    )
    parser.add_argument(
        "--save-publication-manifest-json",
        required=True,
        help="Caminho local para salvar o manifesto",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        drafts = JsonMessageDraftStore(path=Path(args.approved_messages_json)).load()
        manifest = create_publication_manifest(
            drafts=drafts,
            target=args.target,
            created_at=_utc_now_iso(),
        )
        JsonPublicationManifestStore(
            path=Path(args.save_publication_manifest_json)
        ).save(manifest)
    except (
        MessageDraftStoreError,
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


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
