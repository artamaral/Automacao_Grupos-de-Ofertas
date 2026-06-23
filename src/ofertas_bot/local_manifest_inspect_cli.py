from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspeciona manifesto local em JSON")
    parser.add_argument(
        "--manifest-json",
        required=True,
        help="Caminho do arquivo local de manifesto",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        items = _load_manifest(path=Path(args.manifest_json))
    except ValueError as error:
        return _print_inspect_error(error=error)

    if not items:
        print("INFO | Manifesto local vazio.")
        print("INFO | Nenhum envio foi executado.")
        return 0

    for item_number, item in enumerate(items, start=1):
        print(_format_item(item_number=item_number, item=item))

    print("INFO | Nenhum envio foi executado.")
    return 0


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        msg = f"Não foi possível ler {path}"
        raise ValueError(msg) from error
    except json.JSONDecodeError as error:
        msg = "Manifesto local não contém JSON válido"
        raise ValueError(msg) from error

    if not isinstance(payload, list):
        msg = "Manifesto local deve conter uma lista"
        raise ValueError(msg)

    items: list[dict[str, Any]] = []
    for raw_item in payload:
        if not isinstance(raw_item, dict):
            msg = "Cada item do manifesto deve ser um objeto"
            raise ValueError(msg)
        items.append(raw_item)
    return items


def _format_item(item_number: int, item: dict[str, Any]) -> str:
    draft = _dict_value(item, "draft")
    offer = _dict_value(draft, "offer")
    return (
        f"ITEM | {item_number} | status={item.get('status', '-')} | "
        f"target={item.get('target', '-')} | "
        f"created_at={item.get('created_at', '-')} | "
        f"marketplace={offer.get('marketplace', '-')} | "
        f"niche={offer.get('niche', '-')} | "
        f"price=R$ {float(offer.get('price', 0)):.2f} | "
        f"title={offer.get('title', '-')}"
    )


def _dict_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if isinstance(value, dict):
        return value
    return {}


def _print_inspect_error(error: Exception) -> int:
    print("ERRO | Não foi possível inspecionar o manifesto local", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminho e formato do manifesto.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
