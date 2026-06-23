from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Sequence
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Calcula hash de arquivo local")
    parser.add_argument(
        "--file",
        required=True,
        help="Caminho do arquivo local",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = Path(args.file)

    try:
        content = path.read_bytes()
    except OSError as error:
        return _print_hash_error(path=path, error=error)

    print(f"INFO | Arquivo: {path}")
    print(f"INFO | Tamanho: {len(content)} bytes")
    print(f"INFO | SHA-256: {hashlib.sha256(content).hexdigest()}")
    print("INFO | Nenhum envio foi executado.")
    return 0


def _print_hash_error(path: Path, error: Exception) -> int:
    print("ERRO | Não foi possível calcular hash do arquivo", file=sys.stderr)
    print(f"DETALHE | {path}: {error}", file=sys.stderr)
    print("AÇÃO | Verifique se o caminho existe e pode ser lido.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
