from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Conta itens de um manifesto JSON local")
    parser.add_argument(
        "--manifest-json",
        required=True,
        help="Caminho do arquivo local de manifesto",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        items = _load_items(path=Path(args.manifest_json))
    except ValueError as error:
        return _print_count_error(error=error)

    status_counts = Counter(str(item.get("status", "unknown")) for item in items)
    print(f"INFO | Total: {len(items)}")
    for status, count in sorted(status_counts.items()):
        print(f"INFO | {status}: {count}")
    print("INFO | Nenhum envio foi executado.")
    return 0


def _load_items(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        msg = f"Não foi possível ler {path}"
        raise ValueError(msg) from error
    except json.JSONDecodeError as error:
        msg = "Arquivo local não contém JSON válido"
        raise ValueError(msg) from error

    if not isinstance(payload, list):
        msg = "Arquivo local deve conter uma lista"
        raise ValueError(msg)

    items: list[dict[str, Any]] = []
    for raw_item in payload:
        if not isinstance(raw_item, dict):
            msg = "Cada item deve ser um objeto"
            raise ValueError(msg)
        items.append(raw_item)
    return items


def _print_count_error(error: Exception) -> int:
    print("ERRO | Não foi possível contar o manifesto local", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminho e formato do arquivo.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
