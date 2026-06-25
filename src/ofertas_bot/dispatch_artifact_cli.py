from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ofertas_bot.storage.json_publication_manifest_store import (
    JsonPublicationManifestStore,
    PublicationManifestItem,
    PublicationManifestStoreError,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera artefato local de disparo a partir do manifesto"
    )
    parser.add_argument(
        "--manifest-json",
        required=True,
        help="Caminho do arquivo local de manifesto",
    )
    parser.add_argument(
        "--save-dispatch-artifact-json",
        required=True,
        help="Caminho local para salvar o artefato de disparo",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        manifest = JsonPublicationManifestStore(path=Path(args.manifest_json)).load()
        artifact = build_dispatch_artifact(manifest)
        output_path = Path(args.save_dispatch_artifact_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (OSError, PublicationManifestStoreError, ValueError) as error:
        return _print_dispatch_error(error=error)

    print(f"INFO | Artefato de disparo salvo em {args.save_dispatch_artifact_json}")
    print(f"INFO | Total de destinos: {artifact['summary']['total_targets']}")
    print(f"INFO | Total de mensagens: {artifact['summary']['total_messages']}")
    print("INFO | Nenhum envio foi executado.")
    return 0


def build_dispatch_artifact(
    manifest: tuple[PublicationManifestItem, ...],
) -> dict[str, Any]:
    if not manifest:
        raise ValueError("Manifesto local vazio")

    grouped_items: dict[str, list[dict[str, Any]]] = {}
    for item_number, item in enumerate(manifest, start=1):
        if item.status != "ready":
            raise ValueError("Manifesto possui item fora do status ready")

        grouped_items.setdefault(item.target, []).append(
            {
                "manifest_item_number": item_number,
                "status": item.status,
                "created_at": item.created_at,
                "text": item.draft.text,
                "offer": {
                    "marketplace": item.draft.offer.marketplace.value,
                    "niche": item.draft.offer.niche,
                    "title": item.draft.offer.title,
                    "url": item.draft.offer.url,
                    "price": item.draft.offer.price,
                    "old_price": item.draft.offer.old_price,
                },
            }
        )

    targets = [
        {
            "target": target,
            "status": "ready",
            "message_count": len(messages),
            "messages": messages,
        }
        for target, messages in sorted(grouped_items.items())
    ]

    return {
        "generated_at": _utc_now_iso(),
        "summary": {
            "total_targets": len(targets),
            "total_messages": sum(target["message_count"] for target in targets),
        },
        "targets": targets,
    }


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _print_dispatch_error(error: Exception) -> int:
    print("ERRO | Não foi possível gerar o artefato de disparo", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminho e formato do manifesto local.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
