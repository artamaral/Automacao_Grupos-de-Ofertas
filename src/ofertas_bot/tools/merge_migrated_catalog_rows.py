from __future__ import annotations

import argparse
import csv
import json
import re
from collections.abc import Sequence
from pathlib import Path

MIGRATION_PATTERN = re.compile(
    r"partos?|gestante|gesta[cç][aã]o|beb[eê]s?|menino|maternidade|matern[ao]l?|"
    r"gr[aá]vida|amamenta[cç][aã]o|sa[ií]da\s*maternidade|p[oó]s\s*-?\s*parto",
    re.IGNORECASE,
)
TEXT_FIELDS = ("productName", "shopName", "productLink", "offerLink")
IDENTITY_FIELDS = ("shopId", "itemId")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Move linhas do catalogo-fonte que devem sair de um profile e entrar em outro."
        )
    )
    parser.add_argument("--source", required=True, type=Path, help="CSV de origem")
    parser.add_argument("--target", required=True, type=Path, help="CSV base de destino")
    parser.add_argument("--output", required=True, type=Path, help="CSV de saida")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = merge_catalog_rows(
        source_path=args.source,
        target_path=args.target,
        output_path=args.output,
    )
    print(
        "INFO | merge_migrated_catalog_rows "
        f"target_rows={summary['target_rows']} "
        f"migrated_candidates={summary['migrated_candidates']} "
        f"migrated_added={summary['migrated_added']} "
        f"output_rows={summary['output_rows']}"
    )
    return 0


def merge_catalog_rows(
    *,
    source_path: Path,
    target_path: Path,
    output_path: Path,
) -> dict[str, int]:
    source_rows, source_fieldnames = _load_rows(source_path)
    target_rows, target_fieldnames = _load_rows(target_path)
    if source_fieldnames != target_fieldnames:
        raise SystemExit("source and target catalogs must share the same schema")

    existing_keys = {_identity_key(row) for row in target_rows}
    migrated_candidates = []
    for row in source_rows:
        if _identity_key(row) in existing_keys or not _should_migrate(row):
            continue
        migrated_candidates.append(_prepare_migrated_row(row))
    output_rows = target_rows + migrated_candidates
    _write_rows(output_path, target_fieldnames, output_rows)
    return {
        "target_rows": len(target_rows),
        "migrated_candidates": len(migrated_candidates),
        "migrated_added": len(migrated_candidates),
        "output_rows": len(output_rows),
    }


def _load_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def _write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _identity_key(row: dict[str, str]) -> str:
    return ":".join((row.get(field) or "").strip() for field in IDENTITY_FIELDS)


def _should_migrate(row: dict[str, str]) -> bool:
    haystack = " ".join((row.get(field) or "") for field in TEXT_FIELDS)
    return bool(MIGRATION_PATTERN.search(haystack))


def _prepare_migrated_row(row: dict[str, str]) -> dict[str, str]:
    prepared = dict(row)
    marker = _migration_source_hit(row)
    if marker is None:
        return prepared
    hits = _parse_source_hits(prepared.get("source_hits"))
    if marker not in hits:
        hits.append(marker)
    prepared["source_hits"] = json.dumps(hits, ensure_ascii=False)
    return prepared


def _migration_source_hit(row: dict[str, str]) -> str | None:
    product_name = (row.get("productName") or "").lower()
    if "bolsa maternidade" in product_name:
        return "keyword:bolsa maternidade"
    if "mochila maternidade" in product_name:
        return "keyword:mochila maternidade"
    if "saída maternidade" in product_name or "saida maternidade" in product_name:
        return "keyword:saida maternidade"
    if "body bebê" in product_name or "body bebe" in product_name:
        return "keyword:body bebê"
    if "macacão bebê" in product_name or "macacao bebê" in product_name:
        return "keyword:macacão bebê"
    if "roupa bebê" in product_name or "roupa bebe" in product_name:
        return "keyword:roupa bebê"
    if re.search(r"gestante|gr[aá]vida|amamenta[cç][aã]o|p[oó]s\s*-?\s*parto|\bparto\b", product_name):
        if "vestido" in product_name:
            return "keyword:vestido gestante"
        return "keyword:roupa gestante"
    if re.search(r"beb[eê]|menino|maternidade", product_name):
        return "keyword:roupa bebê"
    return None


def _parse_source_hits(value: str | None) -> list[str]:
    if not value:
        return []
    text = value.strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [text]
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item).strip()]
    if isinstance(parsed, str):
        return [parsed]
    return []


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
