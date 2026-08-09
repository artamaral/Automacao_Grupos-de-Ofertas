from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol

from ofertas_bot.catalog_contract import (
    OPERATIONAL_CATALOG_FIELDNAMES,
    project_operational_catalog_row,
)
from ofertas_bot.discovery_profiles import DiscoveryProfileError, load_discovery_profile_catalog
from ofertas_bot.providers.http import ProviderHttpError
from ofertas_bot.providers.real_http_guard import RealHttpValidationError
from ofertas_bot.providers.shopee import ShopeeConfigurationError, ShopeeProvider
from ofertas_bot.providers.shopee_graphql import ShopeeGraphqlPayloadError
from ofertas_bot.providers.transport import HttpTransportError
from ofertas_bot.settings import get_settings
from ofertas_bot.tools.shopee_catalog_builder import _write_catalog_csv

DEFAULT_OUTPUT_BASE_DIR = Path(".data/catalog_refresh")
DEFAULT_DISCOVERY_PROFILES_FILE = Path("config/discovery_profiles.toml")
REFRESH_FIELDS = [
    "productName",
    "productLink",
    "offerLink",
    "imageUrl",
    "price",
    "priceMax",
    "sales",
    "ratingStar",
    "shopType",
    "sellerCommissionRate",
    "shopeeCommissionRate",
]
NUMERIC_FIELDS = {
    "price",
    "priceMax",
    "sales",
    "ratingStar",
    "sellerCommissionRate",
    "shopeeCommissionRate",
}
DIFF_FIELDNAMES = [
    "source_row_number",
    "itemId",
    "productName_before",
    "productName_after",
    "price_before",
    "price_after",
    "priceMax_before",
    "priceMax_after",
    "discount_percent_before",
    "discount_percent_after",
    "sellerCommissionRate_before",
    "sellerCommissionRate_after",
    "shopeeCommissionRate_before",
    "shopeeCommissionRate_after",
    "sales_before",
    "sales_after",
    "ratingStar_before",
    "ratingStar_after",
    "changed_fields",
]
UNRESOLVED_FIELDNAMES = [
    "source_row_number",
    "itemId",
    "productName",
    "reason",
    "detail",
]


class RefreshCatalogError(RuntimeError):
    """Raised when a catalog refresh cannot be completed safely."""


class ShopeeProductOfferProvider(Protocol):
    def fetch_product_offer_raw_response(
        self,
        *,
        limit: int,
        page: int = 1,
        item_id: int | None = None,
        **kwargs: object,
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class RefreshCatalogPaths:
    output_dir: Path
    candidate_catalog: Path
    refresh_report: Path
    price_diff: Path
    unresolved_items: Path


@dataclass(frozen=True)
class RefreshCatalogResult:
    paths: RefreshCatalogPaths
    report: dict[str, Any]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Revalida preco e sinais do catalogo Shopee por itemId."
    )
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog-file", type=Path, default=None)
    parser.add_argument("--output-base-dir", type=Path, default=DEFAULT_OUTPUT_BASE_DIR)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    return parser


def run(
    argv: Sequence[str] | None = None,
    *,
    provider: ShopeeProductOfferProvider | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        catalog_file = resolve_catalog_file(
            profile_slug=args.profile,
            explicit_catalog_file=args.catalog_file,
        )
        result = refresh_catalog_prices(
            profile_slug=args.profile,
            catalog_file=catalog_file,
            output_base_dir=args.output_base_dir,
            run_id=args.run_id,
            limit=args.limit,
            provider=provider or ShopeeProvider(settings=get_settings()),
        )
    except (
        DiscoveryProfileError,
        RefreshCatalogError,
        RealHttpValidationError,
        ShopeeConfigurationError,
        ShopeeGraphqlPayloadError,
        ProviderHttpError,
        HttpTransportError,
        NotImplementedError,
    ) as error:
        print("ERRO | Refresh de catalogo bloqueado", file=sys.stderr)
        print(f"DETALHE | {error}", file=sys.stderr)
        return 3

    _print_result(result=result, profile_slug=args.profile)
    return 0


def resolve_catalog_file(
    *,
    profile_slug: str,
    explicit_catalog_file: Path | None,
) -> Path:
    if explicit_catalog_file is not None:
        return explicit_catalog_file

    profile = load_discovery_profile_catalog(DEFAULT_DISCOVERY_PROFILES_FILE).get(profile_slug)
    if profile is None:
        raise RefreshCatalogError(f"profile not found: {profile_slug}")
    if not profile.catalog_file:
        raise RefreshCatalogError(f"profile has no catalog_file: {profile_slug}")
    return Path(profile.catalog_file)


def refresh_catalog_prices(
    *,
    profile_slug: str,
    catalog_file: Path,
    output_base_dir: Path = DEFAULT_OUTPUT_BASE_DIR,
    run_id: str | None = None,
    limit: int | None = None,
    provider: ShopeeProductOfferProvider,
) -> RefreshCatalogResult:
    if limit is not None and limit <= 0:
        raise RefreshCatalogError("--limit must be positive")
    if not catalog_file.is_file():
        raise RefreshCatalogError(f"catalog file not found: {catalog_file}")

    resolved_run_id = run_id or datetime.now(UTC).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H-%M-%SZ"
    )
    paths = _build_paths(
        output_base_dir=output_base_dir,
        profile_slug=profile_slug,
        run_id=resolved_run_id,
    )
    paths.output_dir.mkdir(parents=True, exist_ok=True)

    rows = _load_catalog_rows(catalog_file)
    processed_rows = rows[:limit] if limit is not None else rows

    candidate_rows: list[dict[str, Any]] = []
    diff_rows: list[dict[str, Any]] = []
    unresolved_rows: list[dict[str, Any]] = []
    changed_field_counts: Counter[str] = Counter()
    summary_counts: Counter[str] = Counter()

    for index, raw_row in enumerate(processed_rows, start=2):
        projected_row = project_operational_catalog_row(raw_row)
        item_id = _parse_item_id(projected_row.get("itemId"))
        if item_id is None:
            unresolved_rows.append(
                _unresolved_row(
                    row=projected_row,
                    source_row_number=index,
                    reason="invalid_item_id",
                    detail="itemId missing or invalid",
                )
            )
            summary_counts["payload_invalid"] += 1
            continue

        try:
            response = provider.fetch_product_offer_raw_response(
                limit=1,
                page=1,
                item_id=item_id,
            )
        except Exception as error:  # noqa: BLE001 - every failed item must be audited.
            unresolved_rows.append(
                _unresolved_row(
                    row=projected_row,
                    source_row_number=index,
                    reason="api_error",
                    detail=str(error),
                )
            )
            summary_counts["api_error"] += 1
            continue

        node = _extract_single_node(response)
        if node is None:
            unresolved_rows.append(
                _unresolved_row(
                    row=projected_row,
                    source_row_number=index,
                    reason="no_return",
                    detail="productOfferV2 returned no nodes",
                )
            )
            summary_counts["no_return"] += 1
            continue
        if not isinstance(node, dict):
            unresolved_rows.append(
                _unresolved_row(
                    row=projected_row,
                    source_row_number=index,
                    reason="payload_invalid",
                    detail="productOfferV2 node is not an object",
                )
            )
            summary_counts["payload_invalid"] += 1
            continue

        refreshed_row, changed_fields = _apply_node_refresh(projected_row, node)
        refreshed_projected_row = project_operational_catalog_row(refreshed_row)
        if not _sales_is_greater_than_one(refreshed_projected_row.get("sales")):
            unresolved_rows.append(
                _unresolved_row(
                    row=refreshed_projected_row,
                    source_row_number=index,
                    reason="sales_not_greater_than_one",
                    detail="refreshed sales is <= 1",
                )
            )
            summary_counts["sales_not_greater_than_one"] += 1
            continue
        if not _rating_is_at_least_4_8(refreshed_projected_row.get("ratingStar")):
            unresolved_rows.append(
                _unresolved_row(
                    row=refreshed_projected_row,
                    source_row_number=index,
                    reason="rating_below_4_8",
                    detail="refreshed ratingStar is below 4.8",
                )
            )
            summary_counts["rating_below_4_8"] += 1
            continue

        candidate_rows.append(refreshed_projected_row)
        diff_rows.append(
            _diff_row(
                before=projected_row,
                after=refreshed_projected_row,
                source_row_number=index,
                changed_fields=changed_fields,
            )
        )
        if changed_fields:
            summary_counts["updated"] += 1
            changed_field_counts.update(changed_fields)
        else:
            summary_counts["unchanged"] += 1

    _write_catalog_csv(
        paths.candidate_catalog,
        candidate_rows,
        fieldnames=OPERATIONAL_CATALOG_FIELDNAMES,
    )
    _write_csv(paths.price_diff, diff_rows, DIFF_FIELDNAMES)
    _write_csv(paths.unresolved_items, unresolved_rows, UNRESOLVED_FIELDNAMES)

    report = _build_report(
        profile_slug=profile_slug,
        catalog_file=catalog_file,
        run_id=resolved_run_id,
        rows_read=len(rows),
        rows_processed=len(processed_rows),
        candidate_rows=len(candidate_rows),
        unresolved_rows=len(unresolved_rows),
        summary_counts=summary_counts,
        changed_field_counts=changed_field_counts,
        paths=paths,
    )
    paths.refresh_report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return RefreshCatalogResult(paths=paths, report=report)


def _build_paths(
    *,
    output_base_dir: Path,
    profile_slug: str,
    run_id: str,
) -> RefreshCatalogPaths:
    output_dir = output_base_dir / profile_slug / run_id
    return RefreshCatalogPaths(
        output_dir=output_dir,
        candidate_catalog=output_dir / "candidate_catalog.csv",
        refresh_report=output_dir / "refresh_report.json",
        price_diff=output_dir / "price_diff.csv",
        unresolved_items=output_dir / "unresolved_items.csv",
    )


def _load_catalog_rows(catalog_file: Path) -> list[dict[str, str]]:
    with catalog_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = sorted(set(OPERATIONAL_CATALOG_FIELDNAMES) - set(fieldnames))
        if missing:
            raise RefreshCatalogError(f"catalog fields missing: {missing}")
        return list(reader)


def _parse_item_id(value: object) -> int | None:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return None


def _extract_single_node(response: dict[str, Any]) -> object | None:
    connection = response.get("data", {}).get("productOfferV2", {})
    nodes = connection.get("nodes", []) if isinstance(connection, dict) else []
    if not isinstance(nodes, list) or not nodes:
        return None
    return nodes[0]


def _apply_node_refresh(
    row: dict[str, Any],
    node: dict[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    refreshed = dict(row)
    changed_fields: list[str] = []
    for field in REFRESH_FIELDS:
        if field not in node or node[field] in (None, ""):
            continue
        candidate_value = node[field]
        if not _values_equal(field, row.get(field), candidate_value):
            refreshed[field] = candidate_value
            changed_fields.append(field)
    return refreshed, tuple(changed_fields)


def _values_equal(field: str, left: object, right: object) -> bool:
    if field in NUMERIC_FIELDS:
        left_decimal = _optional_decimal(left)
        right_decimal = _optional_decimal(right)
        if left_decimal is not None and right_decimal is not None:
            return left_decimal == right_decimal
    if field == "shopType":
        return project_operational_catalog_row({"shopType": left}).get(
            "shopType"
        ) == project_operational_catalog_row({"shopType": right}).get("shopType")
    return str(left or "").strip() == str(right or "").strip()


def _sales_is_greater_than_one(value: object) -> bool:
    numeric = _optional_decimal(value)
    return numeric is not None and numeric > Decimal("1")


def _rating_is_at_least_4_8(value: object) -> bool:
    numeric = _optional_decimal(value)
    return numeric is not None and numeric >= Decimal("4.8")


def _diff_row(
    *,
    before: dict[str, Any],
    after: dict[str, Any],
    source_row_number: int,
    changed_fields: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "source_row_number": source_row_number,
        "itemId": after.get("itemId"),
        "productName_before": before.get("productName"),
        "productName_after": after.get("productName"),
        "price_before": before.get("price"),
        "price_after": after.get("price"),
        "priceMax_before": before.get("priceMax"),
        "priceMax_after": after.get("priceMax"),
        "discount_percent_before": _discount_percent(before),
        "discount_percent_after": _discount_percent(after),
        "sellerCommissionRate_before": before.get("sellerCommissionRate"),
        "sellerCommissionRate_after": after.get("sellerCommissionRate"),
        "shopeeCommissionRate_before": before.get("shopeeCommissionRate"),
        "shopeeCommissionRate_after": after.get("shopeeCommissionRate"),
        "sales_before": before.get("sales"),
        "sales_after": after.get("sales"),
        "ratingStar_before": before.get("ratingStar"),
        "ratingStar_after": after.get("ratingStar"),
        "changed_fields": ",".join(changed_fields),
    }


def _discount_percent(row: dict[str, Any]) -> str:
    price = _optional_decimal(row.get("price"))
    reference = _optional_decimal(row.get("priceMax"))
    if price is None or reference is None or reference <= price or reference <= 0:
        return "0.00"
    return str((((reference - price) / reference) * Decimal("100")).quantize(Decimal("0.01")))


def _optional_decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def _unresolved_row(
    *,
    row: dict[str, Any],
    source_row_number: int,
    reason: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "source_row_number": source_row_number,
        "itemId": row.get("itemId"),
        "productName": row.get("productName"),
        "reason": reason,
        "detail": detail,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_report(
    *,
    profile_slug: str,
    catalog_file: Path,
    run_id: str,
    rows_read: int,
    rows_processed: int,
    candidate_rows: int,
    unresolved_rows: int,
    summary_counts: Counter[str],
    changed_field_counts: Counter[str],
    paths: RefreshCatalogPaths,
) -> dict[str, Any]:
    return {
        "profile": profile_slug,
        "run_id": run_id,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "source_catalog_path": catalog_file.as_posix(),
        "outputs": {
            "candidate_catalog": paths.candidate_catalog.as_posix(),
            "refresh_report": paths.refresh_report.as_posix(),
            "price_diff": paths.price_diff.as_posix(),
            "unresolved_items": paths.unresolved_items.as_posix(),
        },
        "summary": {
            "rows_read": rows_read,
            "rows_processed": rows_processed,
            "candidate_rows": candidate_rows,
            "updated_rows": summary_counts["updated"],
            "unchanged_rows": summary_counts["unchanged"],
            "unresolved_rows": unresolved_rows,
            "no_return_rows": summary_counts["no_return"],
            "payload_invalid_rows": summary_counts["payload_invalid"],
            "api_error_rows": summary_counts["api_error"],
            "sales_not_greater_than_one_rows": summary_counts[
                "sales_not_greater_than_one"
            ],
            "rating_below_4_8_rows": summary_counts["rating_below_4_8"],
            "changed_field_counts": dict(sorted(changed_field_counts.items())),
        },
    }


def _print_result(*, result: RefreshCatalogResult, profile_slug: str) -> None:
    print("INFO | Refresh de catalogo concluido")
    print(f"INFO | candidate_catalog={result.paths.candidate_catalog}")
    print(f"INFO | refresh_report={result.paths.refresh_report}")
    print(f"INFO | price_diff={result.paths.price_diff}")
    print(f"INFO | unresolved_items={result.paths.unresolved_items}")
    print(
        "INFO | summary="
        + json.dumps(result.report["summary"], ensure_ascii=False, sort_keys=True)
    )
    print("INFO | Proximo passo sugerido: validar sem escrita remota")
    print(
        ".\\.venv\\Scripts\\python.exe scripts\\supabase\\import_catalog.py "
        f"--profile {profile_slug} --catalog-file {result.paths.candidate_catalog}"
    )
    print("INFO | Importacao staged opcional, sem ativar")
    print(
        ".\\.venv\\Scripts\\python.exe scripts\\supabase\\import_catalog.py "
        f"--profile {profile_slug} --catalog-file {result.paths.candidate_catalog} "
        "--apply --confirm-remote-write IMPORT_CURATED_CATALOG"
    )


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
