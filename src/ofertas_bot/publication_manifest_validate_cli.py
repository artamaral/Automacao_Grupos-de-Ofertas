from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ofertas_bot.storage.json_publication_manifest_store import (
    JsonPublicationManifestStore,
    PublicationManifestStoreError,
    validate_publication_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida manifesto local de publicação futura")
    parser.add_argument(
        "--publication-manifest-json",
        required=True,
        help="Caminho do arquivo local publication_manifest.json",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = JsonPublicationManifestStore(path=Path(args.publication_manifest_json))

    try:
        issues = validate_publication_manifest(store.load())
    except PublicationManifestStoreError as error:
        return _print_validation_error(error=error)

    if issues:
        print("ERRO | Manifesto local bloqueado.", file=sys.stderr)
        for issue in issues:
            print(f"DETALHE | {issue}", file=sys.stderr)
        print("AÇÃO | Corrija o manifesto antes de qualquer publicação futura.", file=sys.stderr)
        return 3

    print("INFO | Manifesto local validado com sucesso.")
    print("INFO | Nenhum envio foi executado.")
    return 0


def _print_validation_error(error: Exception) -> int:
    print("ERRO | Não foi possível validar o manifesto local", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminho e formato do manifesto.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
