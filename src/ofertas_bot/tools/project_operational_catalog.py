from __future__ import annotations

import argparse
import csv
from collections.abc import Sequence
from pathlib import Path

from ofertas_bot.catalog_contract import (
    OPERATIONAL_CATALOG_FIELDNAMES,
    project_operational_catalog_row,
)
from ofertas_bot.tools.shopee_catalog_builder import _write_catalog_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Projeta um catalogo curado no contrato operacional minimo",
    )
    parser.add_argument("--input", required=True, type=Path, help="CSV de entrada")
    parser.add_argument("--output", type=Path, default=None, help="CSV de saida")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Sobrescreve o proprio arquivo de entrada",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path: Path = args.input
    output_path: Path | None = args.output

    if args.in_place and output_path is not None:
        raise SystemExit("Nao use --output junto com --in-place")
    if not args.in_place and output_path is None:
        raise SystemExit("Informe --output ou use --in-place")

    target_path = input_path if args.in_place else output_path
    assert target_path is not None

    rows = _load_rows(input_path)
    projected_rows = [
        project_operational_catalog_row(row)
        for row in rows
        if _sales_is_greater_than_one(row.get("sales"))
    ]
    _write_catalog_csv(
        target_path,
        projected_rows,
        fieldnames=OPERATIONAL_CATALOG_FIELDNAMES,
    )
    print(f"INFO | Catalogo operacional salvo em {target_path}")
    print(f"INFO | rows={len(projected_rows)}")
    print(
        "INFO | fields="
        + ",".join(OPERATIONAL_CATALOG_FIELDNAMES)
    )
    return 0


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _sales_is_greater_than_one(value: str | None) -> bool:
    if value is None:
        return False
    try:
        return float(value) > 1
    except ValueError:
        return False


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
