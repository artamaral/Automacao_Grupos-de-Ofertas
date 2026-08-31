from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ofertas_bot.catalog_contract import OPERATIONAL_CATALOG_FIELDNAMES
from ofertas_bot.productcatid_catalog import (
    ProductCatIdCatalogError,
    load_product_category_quotas,
    validate_no_cross_category_item_conflicts,
)
from ofertas_bot.shopee_catalog_profiles import load_shopee_catalog_profile_catalog

REQUIRED_FIELDS = {
    "productCatId",
    "itemId",
    "productName",
    "productLink",
    "offerLink",
    "imageUrl",
    "price",
    "sales",
    "ratingStar",
    "commission",
    "shopType",
    "sellerCommissionRate",
    "shopeeCommissionRate",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean a Shopee catalog by singular productCatId without internal taxonomy."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--matrix", type=Path, default=Path("config/shopee_productcatid_quotas_feminino.csv")
    )
    parser.add_argument(
        "--profiles-file", type=Path, default=Path("config/shopee_catalog_profiles.toml")
    )
    return parser.parse_args()


def run(
    *, input_path: Path, output_dir: Path, matrix_path: Path, profiles_path: Path
) -> dict[str, Any]:
    quotas = load_product_category_quotas(matrix_path)
    allowed_ids = {item.product_cat_id for item in quotas}
    profiles = load_shopee_catalog_profile_catalog(profiles_path)
    feminino = profiles.get("feminino")
    if feminino is None:
        raise ProductCatIdCatalogError("feminino profile not found")
    rows = _read_rows(input_path)
    validate_no_cross_category_item_conflicts(rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    clean: list[dict[str, str]] = []
    removed: list[dict[str, str]] = []
    for source_row, row in enumerate(rows, start=2):
        reasons = _row_reasons(
            row, allowed_ids=allowed_ids, forbidden_terms=feminino.negative_terms
        )
        if reasons:
            removed.append(
                row | {"source_row": str(source_row), "removal_reason": "|".join(reasons)}
            )
            continue
        clean.append(row)

    deduplicated, duplicate_rows = _deduplicate_same_category(clean)
    removed.extend(duplicate_rows)
    clean_path = output_dir / "clean_catalog_productcatid_rating_4_5_plus.csv"
    removed_path = output_dir / "removed_rows.csv"
    summary_path = output_dir / "cleaning_report.json"
    _write_clean_catalog(clean_path, deduplicated)
    _write_rows(removed_path, removed)
    summary = {
        "input": str(input_path),
        "input_rows": len(rows),
        "clean_rows": len(deduplicated),
        "removed_rows": len(removed),
        "removed_by_reason": dict(
            sorted(
                Counter(
                    reason for row in removed for reason in row["removal_reason"].split("|")
                ).items()
            )
        ),
        "product_cat_id_counts": dict(
            sorted(Counter(row["productCatId"] for row in deduplicated).items())
        ),
        "outputs": {"clean": str(clean_path), "removed": str(removed_path)},
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary | {"report": str(summary_path)}


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(REQUIRED_FIELDS - set(reader.fieldnames or ()))
        if missing:
            raise ProductCatIdCatalogError(f"raw catalog fields missing: {missing}")
        return list(reader)


def _row_reasons(
    row: dict[str, str], *, allowed_ids: set[int], forbidden_terms: tuple[str, ...]
) -> list[str]:
    reasons: list[str] = []
    try:
        product_cat_id = int(row["productCatId"])
        item_id = int(row["itemId"])
    except (TypeError, ValueError):
        return ["invalid_product_cat_id_or_item_id"]
    if product_cat_id not in allowed_ids:
        reasons.append("product_cat_id_not_allowed")
    if item_id <= 0:
        reasons.append("invalid_item_id")
    if not _positive_decimal(row.get("ratingStar"), minimum=Decimal("4.5")):
        reasons.append("rating_below_4_5")
    if not _positive_decimal(row.get("price")):
        reasons.append("invalid_price")
    if not _positive_decimal(row.get("commission")):
        reasons.append("invalid_commission")
    if not _positive_decimal(row.get("sales"), minimum=Decimal("2")):
        reasons.append("sales_not_greater_than_1")
    if not _is_http_url(row.get("imageUrl")):
        reasons.append("invalid_image_url")
    if not _is_http_url(row.get("offerLink")):
        reasons.append("invalid_offer_link")
    if _forbidden_hits(row, forbidden_terms):
        reasons.append("forbidden_term")
    return reasons


def _deduplicate_same_category(
    rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            -_decimal(row["commission"]),
            -_decimal(row["ratingStar"]),
            -_decimal(row["sales"]),
        ),
    )
    seen: set[int] = set()
    clean: list[dict[str, str]] = []
    removed: list[dict[str, str]] = []
    for row in ranked:
        item_id = int(row["itemId"])
        if item_id in seen:
            removed.append(row | {"removal_reason": "duplicate_item_id_same_product_cat_id"})
        else:
            seen.add(item_id)
            clean.append(row)
    return clean, removed


def _write_clean_catalog(path: Path, rows: list[dict[str, str]]) -> None:
    projected = []
    for row in rows:
        output = {field: row.get(field, "") for field in OPERATIONAL_CATALOG_FIELDNAMES}
        output["subniches"] = "[]"
        projected.append(output)
    _write_rows(path, projected, fieldnames=OPERATIONAL_CATALOG_FIELDNAMES)


def _write_rows(
    path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None
) -> None:
    keys = fieldnames or sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _forbidden_hits(row: dict[str, str], terms: tuple[str, ...]) -> list[str]:
    haystack = _normalize(
        " ".join(
            row.get(field, "") for field in ("productName", "shopName", "productLink", "offerLink")
        )
    )
    return [term for term in terms if _normalize(term) in haystack]


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return re.sub(
        r"\s+", " ", "".join(char for char in decomposed if not unicodedata.combining(char))
    ).strip()


def _positive_decimal(value: str | None, minimum: Decimal = Decimal("0")) -> bool:
    try:
        return _decimal(value) >= minimum
    except (InvalidOperation, TypeError):
        return False


def _decimal(value: str | None) -> Decimal:
    return Decimal(str(value))


def _is_http_url(value: str | None) -> bool:
    return bool(value and value.strip().startswith(("https://", "http://")))


def main() -> None:
    args = parse_args()
    print(
        json.dumps(
            run(
                input_path=args.input,
                output_dir=args.output_dir,
                matrix_path=args.matrix,
                profiles_path=args.profiles_file,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
