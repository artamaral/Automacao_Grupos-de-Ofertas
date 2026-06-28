from __future__ import annotations

import argparse
import csv
import json
import unicodedata
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ofertas_bot.catalog_contract import (
    OPERATIONAL_CATALOG_FIELDNAMES,
    project_operational_catalog_row,
)
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.providers.shopee_graphql import ShopeeGraphqlPayloadError
from ofertas_bot.settings import get_settings
from ofertas_bot.shopee_catalog_profiles import (
    ShopeeCatalogProfile,
    ShopeeCatalogProfileError,
    ShopeeCatalogSubniche,
    load_shopee_catalog_profile_catalog,
)

DEFAULT_OUTPUT_BASE_DIR = Path(".data/shopee_catalog")
DEFAULT_PAGE_SIZE = 50
DEFAULT_MAX_PAGES = 50
CATALOG_FIELDNAMES = [
    "catalog_profile_slug",
    "catalog_profile_name",
    "source_type",
    "source_value",
    "page",
    "limit",
    "hasNextPage",
    "scrollId",
    "itemId",
    "shopId",
    "shopName",
    "productName",
    "productLink",
    "offerLink",
    "imageUrl",
    "commissionRate",
    "appExistRate",
    "appNewRate",
    "webExistRate",
    "webNewRate",
    "commission",
    "price",
    "sales",
    "periodEndTime",
    "periodStartTime",
    "priceMin",
    "priceMax",
    "productCatIds",
    "ratingStar",
    "priceDiscountRate",
    "shopType",
    "sellerCommissionRate",
    "shopeeCommissionRate",
    "source_hits",
    "subniches",
]


@dataclass(frozen=True)
class SourceRun:
    source_type: str
    source_value: str
    row_count: int
    unique_count: int
    page_count: int
    stop_reason: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Constroi catalogo consolidado Shopee a partir de keyword e shopId"
    )
    parser.add_argument("--profile", required=True, help="Slug do catalog profile")
    parser.add_argument(
        "--profiles-file",
        default="config/shopee_catalog_profiles.toml",
        help="Arquivo TOML com catalog profiles da Shopee",
    )
    parser.add_argument(
        "--output-base-dir",
        type=Path,
        default=DEFAULT_OUTPUT_BASE_DIR,
        help="Diretorio base para persistencia da rodada",
    )
    parser.add_argument("--run-id", default=None, help="Identificador opcional da rodada")
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        profile = _load_profile(Path(args.profiles_file), args.profile)
    except ShopeeCatalogProfileError as error:
        print(f"ERRO | {error}")
        return 3

    run_id = args.run_id or datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H-%M-%SZ")
    run_dir = args.output_base_dir / profile.slug / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    provider = ShopeeProvider(settings=get_settings())
    provider.validate_real_http_ready()

    source_runs: list[SourceRun] = []
    raw_source_rows: list[dict[str, Any]] = []
    merged_items: dict[str, dict[str, Any]] = {}
    raw_csv_path = run_dir / "raw_catalog.csv"
    raw_json_path = run_dir / "raw_catalog.json"
    deduplicated_csv_path = run_dir / "deduplicated_catalog.csv"
    deduplicated_json_path = run_dir / "deduplicated_catalog.json"
    clean_csv_path = run_dir / "clean_catalog.csv"
    clean_json_path = run_dir / "clean_catalog.json"
    summary_path = run_dir / "run_summary.json"

    print(f"INFO | profile={profile.slug}")
    print(f"INFO | run_id={run_id}")
    print(f"INFO | output_dir={run_dir}")
    if profile.start_match_ids:
        print(
            "INFO | reference_match_ids="
            + ",".join(str(item) for item in profile.start_match_ids)
        )

    for source_type, source_value, params in _iter_collection_sources(profile):
        items, source_run = _collect_product_offer_pages(
            provider=provider,
            source_type=source_type,
            source_value=source_value,
            params=params,
            page_size=args.page_size,
            max_pages=args.max_pages,
        )
        source_runs.append(source_run)
        raw_source_rows.extend(items)
        _merge_items(merged_items, items)
        _persist_catalog_run(
            profile=profile,
            run_id=run_id,
            raw_source_rows=raw_source_rows,
            merged_items=merged_items,
            source_runs=source_runs,
            raw_csv_path=raw_csv_path,
            raw_json_path=raw_json_path,
            deduplicated_csv_path=deduplicated_csv_path,
            deduplicated_json_path=deduplicated_json_path,
            clean_csv_path=clean_csv_path,
            clean_json_path=clean_json_path,
            summary_path=summary_path,
        )

    print(f"INFO | Catalogo Shopee salvo em {run_dir}")
    final_summary = _build_catalog_summary(
        profile=profile,
        run_id=run_id,
        raw_source_rows=raw_source_rows,
        merged_items=merged_items,
        source_runs=source_runs,
        raw_csv_path=raw_csv_path,
        raw_json_path=raw_json_path,
        deduplicated_csv_path=deduplicated_csv_path,
        deduplicated_json_path=deduplicated_json_path,
        clean_csv_path=clean_csv_path,
        clean_json_path=clean_json_path,
    )
    print(f"INFO | raw_row_count={final_summary['summary']['raw_row_count']}")
    print(f"INFO | deduplicated_item_count={final_summary['summary']['deduplicated_item_count']}")
    print(f"INFO | clean_item_count={final_summary['summary']['clean_item_count']}")
    return 0


def _load_profile(path: Path, slug: str) -> ShopeeCatalogProfile:
    profile = load_shopee_catalog_profile_catalog(path).get(slug)
    if profile is None:
        raise ShopeeCatalogProfileError(f"catalog profile nao encontrado: {slug}")
    return profile


def _iter_collection_sources(
    profile: ShopeeCatalogProfile,
) -> list[tuple[str, str, dict[str, Any]]]:
    sources: list[tuple[str, str, dict[str, Any]]] = []
    for keyword in profile.keyword_terms:
        sources.append(("keyword", keyword, {"keyword": keyword}))
    for shop_id in profile.shop_ids:
        sources.append(("shopId", str(shop_id), {"shop_id": shop_id}))
    return sources


def _collect_product_offer_pages(
    *,
    provider: ShopeeProvider,
    source_type: str,
    source_value: str,
    params: dict[str, Any],
    page_size: int,
    max_pages: int,
) -> tuple[list[dict[str, Any]], SourceRun]:
    rows: list[dict[str, Any]] = []
    unique_keys: set[str] = set()
    page_count = 0
    stop_reason = "max_pages_reached"
    print(f"INFO | source_start type={source_type} value={source_value}")
    for page in range(1, max_pages + 1):
        request_params = dict(params)
        request_params["limit"] = page_size
        request_params["page"] = page
        try:
            response = provider.fetch_product_offer_raw_response(**request_params)
        except ShopeeGraphqlPayloadError as error:
            if "page not found" in str(error).strip().lower():
                stop_reason = "page_not_found"
                break
            raise
        connection = response.get("data", {}).get("productOfferV2", {})
        nodes = connection.get("nodes", []) if isinstance(connection, dict) else []
        page_info = connection.get("pageInfo", {}) if isinstance(connection, dict) else {}
        node_count = len(nodes) if isinstance(nodes, list) else 0
        page_count += 1
        print(
            "INFO | "
            f"source={source_type}:{source_value} "
            f"page={page} node_count={node_count} hasNextPage={page_info.get('hasNextPage')}"
        )

        for node in nodes:
            if not isinstance(node, dict):
                continue
            key = _item_key(node)
            unique_keys.add(key)
            rows.append(_node_to_catalog_row(node=node, page_info=page_info, source_type=source_type, source_value=source_value))

        if node_count == 0:
            stop_reason = "empty_page"
            break
        if page_info.get("hasNextPage") is not True:
            stop_reason = "has_next_page_false"
            break

    print(
        "INFO | "
        f"source_done type={source_type} value={source_value} rows={len(rows)} "
        f"unique={len(unique_keys)} pages={page_count} stop={stop_reason}"
    )
    return rows, SourceRun(
        source_type=source_type,
        source_value=source_value,
        row_count=len(rows),
        unique_count=len(unique_keys),
        page_count=page_count,
        stop_reason=stop_reason,
    )


def _node_to_catalog_row(
    *,
    node: dict[str, Any],
    page_info: dict[str, Any],
    source_type: str,
    source_value: str,
) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "source_value": source_value,
        "page": page_info.get("page"),
        "limit": page_info.get("limit"),
        "hasNextPage": page_info.get("hasNextPage"),
        "scrollId": page_info.get("scrollId"),
        "itemId": node.get("itemId"),
        "shopId": node.get("shopId"),
        "shopName": node.get("shopName"),
        "productName": node.get("productName"),
        "productLink": node.get("productLink"),
        "offerLink": node.get("offerLink"),
        "imageUrl": node.get("imageUrl"),
        "commissionRate": node.get("commissionRate"),
        "appExistRate": node.get("appExistRate"),
        "appNewRate": node.get("appNewRate"),
        "webExistRate": node.get("webExistRate"),
        "webNewRate": node.get("webNewRate"),
        "commission": node.get("commission"),
        "price": node.get("price"),
        "sales": node.get("sales"),
        "periodEndTime": node.get("periodEndTime"),
        "periodStartTime": node.get("periodStartTime"),
        "priceMin": node.get("priceMin"),
        "priceMax": node.get("priceMax"),
        "productCatIds": list(node.get("productCatIds") or []),
        "ratingStar": node.get("ratingStar"),
        "priceDiscountRate": node.get("priceDiscountRate"),
        "shopType": list(node.get("shopType") or []),
        "sellerCommissionRate": node.get("sellerCommissionRate"),
        "shopeeCommissionRate": node.get("shopeeCommissionRate"),
        "source_hits": [f"{source_type}:{source_value}"],
    }


def _merge_items(target: dict[str, dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    for row in rows:
        key = f"{row.get('shopId')}:{row.get('itemId')}"
        current = target.get(key)
        if current is None:
            target[key] = row
            continue
        current_hits = list(current.get("source_hits") or [])
        for hit in row.get("source_hits") or []:
            if hit not in current_hits:
                current_hits.append(hit)
        current["source_hits"] = current_hits


def _matches_negative_terms(*, item: dict[str, Any], negative_terms: tuple[str, ...]) -> bool:
    if not negative_terms:
        return False
    haystack = _normalize_match_text(
        " ".join(
            str(item.get(field, ""))
            for field in ("productName", "shopName", "productLink", "offerLink")
        )
    )
    normalized_terms = tuple(_normalize_match_text(term) for term in negative_terms)
    return any(term in haystack for term in normalized_terms)


def _classify_subniches(
    *,
    item: dict[str, Any],
    subniches: tuple[ShopeeCatalogSubniche, ...],
) -> list[str]:
    haystack = _normalize_match_text(
        " ".join(
            str(item.get(field, ""))
            for field in ("productName", "shopName", "productLink", "offerLink")
        )
    )
    matched: list[str] = []
    for subniche in subniches:
        negative_terms = tuple(_normalize_match_text(term) for term in subniche.negative_terms)
        keyword_terms = tuple(_normalize_match_text(term) for term in subniche.keyword_terms)
        if negative_terms and any(term in haystack for term in negative_terms):
            continue
        if keyword_terms and any(term in haystack for term in keyword_terms):
            matched.append(subniche.slug)
    return matched


def _normalize_match_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_marks.strip().lower()


def _item_key(node: dict[str, Any]) -> str:
    return f"{node.get('shopId')}:{node.get('itemId')}"


def _write_catalog_csv(
    path: Path,
    rows: list[dict[str, Any]],
    *,
    fieldnames: list[str] | None = None,
) -> None:
    resolved_fieldnames = fieldnames or CATALOG_FIELDNAMES
    serializable_rows: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if "productCatIds" in item:
            item["productCatIds"] = _serialize_csv_value(item.get("productCatIds"))
        if "shopType" in item:
            item["shopType"] = _serialize_csv_value(item.get("shopType"))
        if "source_hits" in item:
            item["source_hits"] = _serialize_csv_value(item.get("source_hits"))
        if "subniches" in item:
            item["subniches"] = _serialize_csv_value(item.get("subniches"))
        serializable_rows.append(item)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=resolved_fieldnames)
        writer.writeheader()
        writer.writerows(serializable_rows)


def _serialize_csv_value(value: Any) -> Any:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _persist_catalog_run(
    *,
    profile: ShopeeCatalogProfile,
    run_id: str,
    raw_source_rows: list[dict[str, Any]],
    merged_items: dict[str, dict[str, Any]],
    source_runs: list[SourceRun],
    raw_csv_path: Path,
    raw_json_path: Path,
    deduplicated_csv_path: Path,
    deduplicated_json_path: Path,
    clean_csv_path: Path,
    clean_json_path: Path,
    summary_path: Path,
) -> None:
    summary_payload = _build_catalog_summary(
        profile=profile,
        run_id=run_id,
        raw_source_rows=raw_source_rows,
        merged_items=merged_items,
        source_runs=source_runs,
        raw_csv_path=raw_csv_path,
        raw_json_path=raw_json_path,
        deduplicated_csv_path=deduplicated_csv_path,
        deduplicated_json_path=deduplicated_json_path,
        clean_csv_path=clean_csv_path,
        clean_json_path=clean_json_path,
    )
    deduplicated_items = _build_deduplicated_items(profile=profile, merged_items=merged_items)
    clean_items = _build_clean_items(profile=profile, deduplicated_items=deduplicated_items)
    operational_clean_items = [
        project_operational_catalog_row(item)
        for item in clean_items
    ]
    _write_catalog_csv(raw_csv_path, raw_source_rows)
    raw_json_path.write_text(json.dumps(raw_source_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_catalog_csv(deduplicated_csv_path, deduplicated_items)
    deduplicated_json_path.write_text(
        json.dumps(deduplicated_items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_catalog_csv(
        clean_csv_path,
        operational_clean_items,
        fieldnames=OPERATIONAL_CATALOG_FIELDNAMES,
    )
    clean_json_path.write_text(
        json.dumps(operational_clean_items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "INFO | "
        f"checkpoint raw={summary_payload['summary']['raw_row_count']} "
        f"deduplicated={summary_payload['summary']['deduplicated_item_count']} "
        f"clean={summary_payload['summary']['clean_item_count']}"
    )


def _build_catalog_summary(
    *,
    profile: ShopeeCatalogProfile,
    run_id: str,
    raw_source_rows: list[dict[str, Any]],
    merged_items: dict[str, dict[str, Any]],
    source_runs: list[SourceRun],
    raw_csv_path: Path,
    raw_json_path: Path,
    deduplicated_csv_path: Path,
    deduplicated_json_path: Path,
    clean_csv_path: Path,
    clean_json_path: Path,
) -> dict[str, Any]:
    deduplicated_items = _build_deduplicated_items(profile=profile, merged_items=merged_items)
    clean_items = _build_clean_items(profile=profile, deduplicated_items=deduplicated_items)
    return {
        "profile": {
            "slug": profile.slug,
            "name": profile.name,
            "start_match_ids": list(profile.start_match_ids),
            "keyword_terms": list(profile.keyword_terms),
            "negative_terms": list(profile.negative_terms),
            "shop_ids": list(profile.shop_ids),
            "shop_names": list(profile.shop_names),
        },
        "run_id": run_id,
        "source_runs": [asdict(item) for item in source_runs],
        "summary": {
            "raw_row_count": len(raw_source_rows),
            "deduplicated_item_count": len(deduplicated_items),
            "clean_item_count": len(clean_items),
            "negative_terms_count": len(profile.negative_terms),
            "subniche_count": len(profile.subniches),
            "unresolved_shop_names": list(profile.shop_names),
        },
        "paths": {
            "raw_csv": str(raw_csv_path),
            "raw_json": str(raw_json_path),
            "deduplicated_csv": str(deduplicated_csv_path),
            "deduplicated_json": str(deduplicated_json_path),
            "clean_csv": str(clean_csv_path),
            "clean_json": str(clean_json_path),
        },
    }


def _build_deduplicated_items(
    *,
    profile: ShopeeCatalogProfile,
    merged_items: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    items = [dict(item) for item in merged_items.values()]
    for item in items:
        item["catalog_profile_slug"] = profile.slug
        item["catalog_profile_name"] = profile.name
        item.setdefault("subniches", [])
    return items


def _build_clean_items(
    *,
    profile: ShopeeCatalogProfile,
    deduplicated_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    clean_items = [
        dict(item)
        for item in deduplicated_items
        if not _matches_negative_terms(item=item, negative_terms=profile.negative_terms)
    ]
    for item in clean_items:
        item["catalog_profile_slug"] = profile.slug
        item["catalog_profile_name"] = profile.name
        item["subniches"] = _classify_subniches(item=item, subniches=profile.subniches)
    return clean_items


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
