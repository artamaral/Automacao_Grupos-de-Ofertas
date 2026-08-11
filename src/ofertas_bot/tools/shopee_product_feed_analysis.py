from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import mean, median
from typing import Any
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv

ACTIVE_CATALOG_QUERY = """
select
  imp.id as import_id,
  imp.profile,
  imp.marketplace,
  imp.row_count,
  item.item_id,
  item.product_name,
  item.product_link,
  item.offer_link,
  item.image_url,
  item.price,
  item.reference_price,
  item.sales_count,
  item.rating,
  item.shop_type_codes,
  item.seller_commission_rate,
  item.shopee_commission_rate,
  item.commission_rate_fallback,
  item.is_free_shipping,
  item.subniches,
  item.source_payload
from offers.catalog_imports imp
join offers.catalog_items item
  on item.import_id = imp.id
where imp.status = 'active'
order by imp.profile, item.item_id
"""

DEFAULT_OUTPUT_BASE_DIR = Path(".data/feed_vs_catalog_analysis")
DEFAULT_DOWNLOADS_DIR = Path.home() / "Downloads"
DEFAULT_FEED_10K_PATTERN = "*Shopee Brasil - 2022*.csv"
DEFAULT_FEED_100K_PATTERN = "*Shopee Oficial BR - 2022*.csv"
DEFAULT_PROCESSED_CATALOGS = {
    "auto-e-moto": Path("catalogs/processed/auto-e-moto/shopee_catalogo_limpo_subniches.csv"),
    "feminino": Path("catalogs/processed/feminino/shopee_catalogo_limpo_subniches.csv"),
    "mae-e-bebe": Path("catalogs/processed/mae-e-bebe/shopee_catalogo_limpo_subniches.csv"),
}


@dataclass(frozen=True)
class DatasetAudit:
    rows: int
    distinct_item_ids: int
    distinct_shop_ids: int
    null_item_ids: int
    null_shop_ids: int
    duplicated_item_id_rows: int
    duplicated_item_id_keys: int
    duplicated_item_shop_rows: int
    duplicated_item_shop_keys: int
    item_id_storage: str
    shop_id_storage: str
    item_id_normalization: str
    shop_id_normalization: str


@dataclass(frozen=True)
class OverlapSummary:
    left_distinct: int
    right_distinct: int
    overlap: int
    left_only: int
    right_only: int
    left_overlap_percent: float
    right_overlap_percent: float


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Analisa em modo read-only o catalogo Shopee ativo no Supabase "
            "versus Product Feeds."
        )
    )
    parser.add_argument("--output-base-dir", type=Path, default=DEFAULT_OUTPUT_BASE_DIR)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--feed-10k", type=Path, default=None)
    parser.add_argument("--feed-100k", type=Path, default=None)
    parser.add_argument("--downloads-dir", type=Path, default=DEFAULT_DOWNLOADS_DIR)
    parser.add_argument(
        "--database-url-env",
        default="SUPABASE_DB_URL",
        help="Nome da variavel de ambiente com a string de conexao do Supabase",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    load_dotenv(Path(".env"))
    database_url = os.getenv(args.database_url_env)
    if not database_url:
        raise SystemExit(f"{args.database_url_env} is required")

    run_id = args.run_id or datetime.now(UTC).strftime("%Y-%m-%d")
    output_dir = args.output_base_dir / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    feed_10k_path = args.feed_10k or _discover_latest_feed(
        downloads_dir=args.downloads_dir,
        pattern=DEFAULT_FEED_10K_PATTERN,
    )
    feed_100k_path = args.feed_100k or _discover_latest_feed(
        downloads_dir=args.downloads_dir,
        pattern=DEFAULT_FEED_100K_PATTERN,
    )

    catalog_rows = _load_active_catalog(database_url)
    enrichment_rows = _load_processed_catalog_enrichment(DEFAULT_PROCESSED_CATALOGS)
    catalog_records = _build_catalog_records(catalog_rows, enrichment_rows)
    feed_10k_records = _load_feed_records(feed_10k_path, feed_kind="feed_10k")
    feed_100k_records = _load_feed_records(feed_100k_path, feed_kind="feed_100k")

    analysis = _build_analysis(
        catalog_records=catalog_records,
        feed_10k_records=feed_10k_records,
        feed_100k_records=feed_100k_records,
        feed_10k_path=feed_10k_path,
        feed_100k_path=feed_100k_path,
    )

    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _write_overlap_csv(
        output_dir / "catalog_vs_feed100k_overlap.csv",
        _filter_records_by_item_ids(
            catalog_records,
            set(analysis["overlap_examples"]["catalog_vs_feed100k_item_ids"]),
        ),
    )
    _write_overlap_csv(
        output_dir / "catalog_vs_feed10k_overlap.csv",
        _filter_records_by_item_ids(
            catalog_records,
            set(analysis["overlap_examples"]["catalog_vs_feed10k_item_ids"]),
        ),
    )
    _write_overlap_csv(
        output_dir / "feed10k_vs_feed100k_overlap.csv",
        _filter_records_by_item_ids(
            feed_10k_records,
            set(analysis["overlap_examples"]["feed10k_vs_feed100k_item_ids"]),
        ),
    )

    print(f"INFO | summary={summary_path}")
    print(f"INFO | catalog_rows={len(catalog_records)}")
    print(f"INFO | feed_100k_rows={len(feed_100k_records)}")
    print(f"INFO | feed_10k_rows={len(feed_10k_records)}")
    return 0


def _discover_latest_feed(*, downloads_dir: Path, pattern: str) -> Path:
    matches = sorted(
        downloads_dir.glob(pattern),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        raise SystemExit(f"feed file not found with pattern: {downloads_dir / pattern}")
    return matches[0]


def _load_active_catalog(database_url: str) -> list[dict[str, Any]]:
    with psycopg.connect(database_url, connect_timeout=15) as connection:
        with connection.cursor(row_factory=psycopg.rows.dict_row) as cursor:
            cursor.execute(ACTIVE_CATALOG_QUERY)
            return list(cursor.fetchall())


def _load_processed_catalog_enrichment(
    processed_catalogs: dict[str, Path],
) -> dict[tuple[str, str], dict[str, str]]:
    enrichment: dict[tuple[str, str], dict[str, str]] = {}
    for profile, path in processed_catalogs.items():
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                item_id = _normalize_digit_key(row.get("itemId"))
                if item_id is None:
                    continue
                enrichment[(profile, item_id)] = row
    return enrichment


def _build_catalog_records(
    rows: list[dict[str, Any]],
    enrichment_rows: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in rows:
        item_id = _normalize_digit_key(row.get("item_id"))
        if item_id is None:
            continue
        profile = str(row["profile"])
        enrichment = enrichment_rows.get((profile, item_id), {})
        product_link = _string_or_none(row.get("product_link"))
        derived_shop_id = _derive_shop_id_from_product_link(product_link)
        enriched_shop_id = _normalize_digit_key(enrichment.get("shopId"))
        category_ids = _parse_json_like_list(enrichment.get("productCatIds"))
        subniches = _parse_json_like_list(row.get("subniches"))
        source_payload = row.get("source_payload")
        source_payload_keys = (
            sorted(source_payload.keys())
            if isinstance(source_payload, dict)
            else []
        )

        records.append(
            {
                "dataset": "catalog_active",
                "profile": profile,
                "item_id": item_id,
                "shop_id": derived_shop_id or enriched_shop_id,
                "shop_id_from_product_link": derived_shop_id,
                "shop_id_from_processed": enriched_shop_id,
                "shop_name": _string_or_none(enrichment.get("shopName")),
                "product_name": _string_or_none(row.get("product_name")),
                "product_link": product_link,
                "offer_link": _string_or_none(row.get("offer_link")),
                "price_current": _decimal_or_none(row.get("price")),
                "price_reference": _decimal_or_none(row.get("reference_price")),
                "discount_percent": _compute_discount_percent(
                    current=_decimal_or_none(row.get("price")),
                    reference=_decimal_or_none(row.get("reference_price")),
                ),
                "sales_count": _int_or_none(row.get("sales_count")),
                "item_rating": _decimal_or_none(row.get("rating")),
                "shop_rating": None,
                "shop_type_codes": _parse_json_like_list(row.get("shop_type_codes")),
                "subniches": subniches,
                "category_id_level_1": _category_component(category_ids, 0),
                "category_id_level_2": _category_component(category_ids, 1),
                "category_id_level_3": _category_component(category_ids, 2),
                "category_name_level_1": None,
                "category_name_level_2": None,
                "category_name_level_3": None,
                "global_item_attributes": None,
                "mall_flag": None,
                "preferred_flag": None,
                "star_flag": None,
                "official_shop_flag": None,
                "source_payload_keys": source_payload_keys,
            }
        )
    return records


def _load_feed_records(path: Path, *, feed_kind: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            product_link = _string_or_none(row.get("product_link"))
            item_id = _normalize_digit_key(row.get("itemid"))
            records.append(
                {
                    "dataset": feed_kind,
                    "profile": None,
                    "item_id": item_id,
                    "shop_id": _derive_shop_id_from_product_link(product_link),
                    "shop_id_from_product_link": _derive_shop_id_from_product_link(product_link),
                    "shop_id_from_processed": None,
                    "shop_name": _string_or_none(row.get("shop_name")),
                    "product_name": _string_or_none(row.get("title")),
                    "product_link": product_link,
                    "offer_link": _string_or_none(row.get("product_short link")),
                    "price_current": _decimal_or_none(row.get("sale_price")),
                    "price_reference": _decimal_or_none(row.get("price")),
                    "discount_percent": _decimal_or_none(row.get("discount_percentage")),
                    "sales_count": None,
                    "item_rating": _decimal_or_none(row.get("item_rating")),
                    "shop_rating": _decimal_or_none(row.get("shop_rating")),
                    "shop_type_codes": None,
                    "subniches": None,
                    "category_id_level_1": _normalize_digit_key(row.get("global_catid1")),
                    "category_id_level_2": _normalize_digit_key(row.get("global_catid2")),
                    "category_id_level_3": _normalize_digit_key(row.get("global_catid3")),
                    "category_name_level_1": _string_or_none(row.get("global_category1")),
                    "category_name_level_2": _string_or_none(row.get("global_category2")),
                    "category_name_level_3": _string_or_none(row.get("global_category3")),
                    "global_item_attributes": _string_or_none(row.get("global_item_attributes")),
                    "mall_flag": _detect_mall_flag(row),
                    "preferred_flag": None,
                    "star_flag": None,
                    "official_shop_flag": _detect_official_shop_flag(feed_kind=feed_kind, row=row),
                    "source_payload_keys": sorted(row.keys()),
                }
            )
    return records


def _build_analysis(
    *,
    catalog_records: list[dict[str, Any]],
    feed_10k_records: list[dict[str, Any]],
    feed_100k_records: list[dict[str, Any]],
    feed_10k_path: Path,
    feed_100k_path: Path,
) -> dict[str, Any]:
    schema_mapping = _build_schema_mapping()
    audits = {
        "catalog_active": asdict(
            _audit_dataset(
                catalog_records,
                item_id_storage="offers.catalog_items.item_id bigint",
                shop_id_storage="derivado de product_link e validado contra catalogs/processed",
            )
        ),
        "feed_10k": asdict(
            _audit_dataset(
                feed_10k_records,
                item_id_storage="CSV text column itemid",
                shop_id_storage="derivado de product_link",
            )
        ),
        "feed_100k": asdict(
            _audit_dataset(
                feed_100k_records,
                item_id_storage="CSV text column itemid",
                shop_id_storage="derivado de product_link",
            )
        ),
    }

    catalog_item_ids = _distinct_keys(catalog_records, "item_id")
    feed_10k_item_ids = _distinct_keys(feed_10k_records, "item_id")
    feed_100k_item_ids = _distinct_keys(feed_100k_records, "item_id")
    catalog_item_shop = _distinct_pair_keys(catalog_records, "item_id", "shop_id")
    feed_10k_item_shop = _distinct_pair_keys(feed_10k_records, "item_id", "shop_id")
    feed_100k_item_shop = _distinct_pair_keys(feed_100k_records, "item_id", "shop_id")
    catalog_shop_ids = _distinct_keys(catalog_records, "shop_id")
    feed_10k_shop_ids = _distinct_keys(feed_10k_records, "shop_id")
    feed_100k_shop_ids = _distinct_keys(feed_100k_records, "shop_id")

    overlap_catalog_feed100k_item = _overlap_summary(catalog_item_ids, feed_100k_item_ids)
    overlap_catalog_feed100k_item_shop = _overlap_summary(catalog_item_shop, feed_100k_item_shop)
    overlap_catalog_feed10k_item = _overlap_summary(catalog_item_ids, feed_10k_item_ids)
    overlap_catalog_feed10k_item_shop = _overlap_summary(catalog_item_shop, feed_10k_item_shop)
    overlap_feed10k_feed100k_item = _overlap_summary(feed_10k_item_ids, feed_100k_item_ids)
    overlap_feed10k_feed100k_item_shop = _overlap_summary(feed_10k_item_shop, feed_100k_item_shop)

    shop_overlap_catalog_feed100k = _overlap_summary(catalog_shop_ids, feed_100k_shop_ids)
    shop_overlap_catalog_feed10k = _overlap_summary(catalog_shop_ids, feed_10k_shop_ids)
    shop_overlap_feed10k_feed100k = _overlap_summary(feed_10k_shop_ids, feed_100k_shop_ids)

    groups_catalog_vs_feed100k = _split_overlap_groups(
        left_records=catalog_records,
        right_records=feed_100k_records,
        overlap_item_ids=(catalog_item_ids & feed_100k_item_ids),
    )

    category_analysis = _build_category_analysis(
        catalog_records=catalog_records,
        feed_10k_records=feed_10k_records,
        feed_100k_records=feed_100k_records,
        overlap_item_ids_catalog_feed100k=(catalog_item_ids & feed_100k_item_ids),
    )

    return {
        "analysis_date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "sources": {
            "supabase_active_catalog_query": ACTIVE_CATALOG_QUERY.strip(),
            "processed_catalogs": {
                profile: str(path)
                for profile, path in DEFAULT_PROCESSED_CATALOGS.items()
            },
            "feed_10k_path": str(feed_10k_path),
            "feed_100k_path": str(feed_100k_path),
        },
        "schema_mapping": schema_mapping,
        "audits": audits,
        "overlap": {
            "catalog_vs_feed100k": {
                "item_id": asdict(overlap_catalog_feed100k_item),
                "item_id_shop_id": asdict(overlap_catalog_feed100k_item_shop),
                "shop_id": asdict(shop_overlap_catalog_feed100k),
            },
            "catalog_vs_feed10k": {
                "item_id": asdict(overlap_catalog_feed10k_item),
                "item_id_shop_id": asdict(overlap_catalog_feed10k_item_shop),
                "shop_id": asdict(shop_overlap_catalog_feed10k),
            },
            "feed10k_vs_feed100k": {
                "item_id": asdict(overlap_feed10k_feed100k_item),
                "item_id_shop_id": asdict(overlap_feed10k_feed100k_item_shop),
                "shop_id": asdict(shop_overlap_feed10k_feed100k),
            },
        },
        "shop_overlap_diagnostics": {
            "catalog_items_with_shop_also_in_feed100k": _count_records_with_shop_in_set(
                catalog_records,
                feed_100k_shop_ids,
            ),
            "feed100k_items_with_shop_also_in_catalog": _count_records_with_shop_in_set(
                feed_100k_records,
                catalog_shop_ids,
            ),
            "catalog_items_with_shop_also_in_feed10k": _count_records_with_shop_in_set(
                catalog_records,
                feed_10k_shop_ids,
            ),
            "feed10k_items_with_shop_also_in_catalog": _count_records_with_shop_in_set(
                feed_10k_records,
                catalog_shop_ids,
            ),
        },
        "shop_concentration": {
            "catalog_active": _shop_concentration_stats(catalog_records),
            "feed_100k": _shop_concentration_stats(feed_100k_records),
            "feed_10k": _shop_concentration_stats(feed_10k_records),
        },
        "category_analysis": category_analysis,
        "catalog_subniche_distribution": _subniche_distribution(catalog_records),
        "attribute_groups_catalog_vs_feed100k": {
            group_name: _attribute_summary(group_records)
            for group_name, group_records in groups_catalog_vs_feed100k.items()
        },
        "feed10k_vs_feed100k_attributes": {
            "feed_10k": _attribute_summary(feed_10k_records),
            "feed_100k": _attribute_summary(feed_100k_records),
        },
        "intersection_profile_breakdown": _profile_breakdown_for_overlap(
            catalog_records,
            (catalog_item_ids & feed_100k_item_ids),
        ),
        "intersection_specials": {
            "catalog_vs_feed100k": _attribute_summary(
                _filter_records_by_item_ids(
                    catalog_records,
                    (catalog_item_ids & feed_100k_item_ids),
                )
            ),
            "catalog_only": _attribute_summary(groups_catalog_vs_feed100k["catalog_only"]),
            "feed100k_only": _attribute_summary(groups_catalog_vs_feed100k["feed_only"]),
        },
        "feed_subset_checks": {
            "feed10k_item_ids_all_in_feed100k": feed_10k_item_ids <= feed_100k_item_ids,
            "feed10k_item_shop_all_in_feed100k": feed_10k_item_shop <= feed_100k_item_shop,
            "feed10k_shop_ids_all_in_feed100k": feed_10k_shop_ids <= feed_100k_shop_ids,
        },
        "overlap_examples": {
            "catalog_vs_feed100k_item_ids": sorted(catalog_item_ids & feed_100k_item_ids)[:500],
            "catalog_vs_feed10k_item_ids": sorted(catalog_item_ids & feed_10k_item_ids)[:500],
            "feed10k_vs_feed100k_item_ids": sorted(feed_10k_item_ids & feed_100k_item_ids)[:500],
        },
        "future_commission_plan": {
            "endpoint": "productOfferV2",
                "batch_support_observed_in_code": False,
                "evidence": [
                (
                    "src/ofertas_bot/providers/shopee.py::"
                    "fetch_product_offer_raw_response aceita um item_id por chamada"
                ),
                (
                    "src/ofertas_bot/providers/shopee_graphql.py monta query "
                    "com argumento itemId singular"
                ),
                (
                    "docs/status-integracao-shopee.md documenta limit paginado, "
                    "mas nao batch por lista de itemIds"
                ),
            ],
            "documented_limit": (
                "20 por pagina para productOfferV2; "
                "500 por pagina para getItemFeedData"
            ),
            "recommended_sampling": {
                "intersection_catalog_feed100k": min(200, overlap_catalog_feed100k_item.overlap),
                "catalog_only": min(1000, overlap_catalog_feed100k_item.left_only),
                "feed100k_only": min(1000, overlap_catalog_feed100k_item.right_only),
                "feed10k": min(500, len(feed_10k_item_ids)),
            },
            "estimated_calls_if_one_item_per_call": {
                "minimum_recommended_sample": min(200, overlap_catalog_feed100k_item.overlap)
                + min(500, overlap_catalog_feed100k_item.left_only)
                + min(500, overlap_catalog_feed100k_item.right_only)
                + min(250, len(feed_10k_item_ids)),
                "maximum_recommended_sample": min(200, overlap_catalog_feed100k_item.overlap)
                + min(1000, overlap_catalog_feed100k_item.left_only)
                + min(1000, overlap_catalog_feed100k_item.right_only)
                + min(500, len(feed_10k_item_ids)),
            },
        },
    }


def _build_schema_mapping() -> list[dict[str, str]]:
    return [
        {
            "concept": "itemId",
            "catalog": "offers.catalog_items.item_id",
            "feed_100k": "itemid",
            "feed_10k": "itemid",
        },
        {
            "concept": "shopId",
            "catalog": (
                "derivado de product_link e validado com "
                "catalogs/processed/*/shopee_catalogo_limpo_subniches.csv::shopId"
            ),
            "feed_100k": "derivado de product_link",
            "feed_10k": "derivado de product_link",
        },
        {
            "concept": "shopName",
            "catalog": "catalogs/processed/*/shopee_catalogo_limpo_subniches.csv::shopName",
            "feed_100k": "shop_name",
            "feed_10k": "nao disponivel",
        },
        {
            "concept": "category level 1 id",
            "catalog": "catalogs/processed/*/shopee_catalogo_limpo_subniches.csv::productCatIds[0]",
            "feed_100k": "global_catid1",
            "feed_10k": "global_catid1",
        },
        {
            "concept": "category level 2 id",
            "catalog": "catalogs/processed/*/shopee_catalogo_limpo_subniches.csv::productCatIds[1]",
            "feed_100k": "global_catid2",
            "feed_10k": "global_catid2",
        },
        {
            "concept": "category level 3 id",
            "catalog": "catalogs/processed/*/shopee_catalogo_limpo_subniches.csv::productCatIds[2]",
            "feed_100k": "global_catid3",
            "feed_10k": "nao disponivel",
        },
        {
            "concept": "title or name",
            "catalog": "offers.catalog_items.product_name",
            "feed_100k": "title",
            "feed_10k": "title",
        },
        {
            "concept": "current price",
            "catalog": "offers.catalog_items.price",
            "feed_100k": "sale_price",
            "feed_10k": "sale_price",
        },
        {
            "concept": "reference price",
            "catalog": "offers.catalog_items.reference_price",
            "feed_100k": "price",
            "feed_10k": "price",
        },
        {
            "concept": "discount percent",
            "catalog": "derivado de reference_price versus price",
            "feed_100k": "discount_percentage",
            "feed_10k": "discount_percentage",
        },
        {
            "concept": "sales",
            "catalog": "offers.catalog_items.sales_count",
            "feed_100k": "nao disponivel",
            "feed_10k": "nao disponivel",
        },
        {
            "concept": "item rating",
            "catalog": "offers.catalog_items.rating",
            "feed_100k": "item_rating",
            "feed_10k": "item_rating",
        },
        {
            "concept": "shop rating",
            "catalog": "nao disponivel",
            "feed_100k": "shop_rating",
            "feed_10k": "nao disponivel",
        },
        {
            "concept": "shop type",
            "catalog": "offers.catalog_items.shop_type_codes",
            "feed_100k": "nao disponivel",
            "feed_10k": "nao disponivel",
        },
        {
            "concept": "internal taxonomy",
            "catalog": "offers.catalog_items.subniches",
            "feed_100k": "nao disponivel",
            "feed_10k": "nao disponivel",
        },
    ]


def _audit_dataset(
    records: list[dict[str, Any]],
    *,
    item_id_storage: str,
    shop_id_storage: str,
) -> DatasetAudit:
    item_ids = [record["item_id"] for record in records]
    shop_ids = [record["shop_id"] for record in records]
    item_counter = Counter(item_ids)
    pair_counter = Counter((record["item_id"], record["shop_id"]) for record in records)
    return DatasetAudit(
        rows=len(records),
        distinct_item_ids=len({value for value in item_ids if value is not None}),
        distinct_shop_ids=len({value for value in shop_ids if value is not None}),
        null_item_ids=sum(value is None for value in item_ids),
        null_shop_ids=sum(value is None for value in shop_ids),
        duplicated_item_id_rows=sum(
            count - 1
            for key, count in item_counter.items()
            if key is not None and count > 1
        ),
        duplicated_item_id_keys=sum(
            1
            for key, count in item_counter.items()
            if key is not None and count > 1
        ),
        duplicated_item_shop_rows=sum(
            count - 1
            for (item_id, shop_id), count in pair_counter.items()
            if item_id is not None and shop_id is not None and count > 1
        ),
        duplicated_item_shop_keys=sum(
            1
            for (item_id, shop_id), count in pair_counter.items()
            if item_id is not None and shop_id is not None and count > 1
        ),
        item_id_storage=item_id_storage,
        shop_id_storage=shop_id_storage,
        item_id_normalization="strip -> apenas digitos -> comparacao como texto canonico",
        shop_id_normalization=(
            "extraido de /product/<shopId>/<itemId> "
            "e comparado como texto canonico"
        ),
    )


def _distinct_keys(records: list[dict[str, Any]], key: str) -> set[str]:
    return {record[key] for record in records if record.get(key) is not None}


def _distinct_pair_keys(records: list[dict[str, Any]], left_key: str, right_key: str) -> set[str]:
    values = set()
    for record in records:
        left = record.get(left_key)
        right = record.get(right_key)
        if left is None or right is None:
            continue
        values.add(f"{left}:{right}")
    return values


def _overlap_summary(left: set[str], right: set[str]) -> OverlapSummary:
    overlap = left & right
    left_only = left - right
    right_only = right - left
    return OverlapSummary(
        left_distinct=len(left),
        right_distinct=len(right),
        overlap=len(overlap),
        left_only=len(left_only),
        right_only=len(right_only),
        left_overlap_percent=_percent(len(overlap), len(left)),
        right_overlap_percent=_percent(len(overlap), len(right)),
    )


def _count_records_with_shop_in_set(records: list[dict[str, Any]], shop_ids: set[str]) -> int:
    return sum(1 for record in records if record.get("shop_id") in shop_ids)


def _shop_concentration_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(record["shop_id"] for record in records if record.get("shop_id") is not None)
    if not counts:
        return {}
    values = sorted(counts.values())
    top_shops = []
    shop_names: dict[str, str] = {}
    for record in records:
        shop_id = record.get("shop_id")
        shop_name = record.get("shop_name")
        if shop_id and shop_name and shop_id not in shop_names:
            shop_names[shop_id] = shop_name
    for shop_id, count in counts.most_common(20):
        top_shops.append(
            {
                "shop_id": shop_id,
                "shop_name": shop_names.get(shop_id),
                "product_count": count,
            }
        )
    return {
        "shops": len(counts),
        "mean_products_per_shop": round(mean(values), 2),
        "median_products_per_shop": _median(values),
        "p75_products_per_shop": _percentile(values, 75),
        "p90_products_per_shop": _percentile(values, 90),
        "p95_products_per_shop": _percentile(values, 95),
        "top_shops": top_shops,
    }


def _build_category_analysis(
    *,
    catalog_records: list[dict[str, Any]],
    feed_10k_records: list[dict[str, Any]],
    feed_100k_records: list[dict[str, Any]],
    overlap_item_ids_catalog_feed100k: set[str],
) -> dict[str, Any]:
    only_catalog_records = [
        record
        for record in catalog_records
        if record["item_id"] not in overlap_item_ids_catalog_feed100k
    ]
    only_feed_records = [
        record
        for record in feed_100k_records
        if record["item_id"] not in overlap_item_ids_catalog_feed100k
    ]
    overlap_records = [
        record
        for record in feed_100k_records
        if record["item_id"] in overlap_item_ids_catalog_feed100k
    ]

    return {
        "level_1": _category_level_summary(
            catalog_records,
            feed_10k_records,
            feed_100k_records,
            overlap_records,
            only_catalog_records,
            only_feed_records,
            level=1,
        ),
        "level_2": _category_level_summary(
            catalog_records,
            feed_10k_records,
            feed_100k_records,
            overlap_records,
            only_catalog_records,
            only_feed_records,
            level=2,
        ),
        "level_3": _category_level_summary(
            catalog_records,
            feed_10k_records,
            feed_100k_records,
            overlap_records,
            only_catalog_records,
            only_feed_records,
            level=3,
        ),
    }


def _category_level_summary(
    catalog_records: list[dict[str, Any]],
    feed_10k_records: list[dict[str, Any]],
    feed_100k_records: list[dict[str, Any]],
    overlap_records: list[dict[str, Any]],
    only_catalog_records: list[dict[str, Any]],
    only_feed_records: list[dict[str, Any]],
    *,
    level: int,
) -> dict[str, Any]:
    key = f"category_id_level_{level}"
    name_key = f"category_name_level_{level}"
    labels = _category_name_lookup(feed_10k_records + feed_100k_records, key=key, name_key=name_key)
    catalog_counter = Counter(record.get(key) for record in catalog_records if record.get(key))
    feed_counter = Counter(record.get(key) for record in feed_100k_records if record.get(key))
    keys = sorted(set(catalog_counter) | set(feed_counter))
    rows = []
    catalog_total = sum(catalog_counter.values())
    feed_total = sum(feed_counter.values())
    overlap_counter = Counter(record.get(key) for record in overlap_records if record.get(key))
    only_catalog_counter = Counter(
        record.get(key)
        for record in only_catalog_records
        if record.get(key)
    )
    only_feed_counter = Counter(record.get(key) for record in only_feed_records if record.get(key))
    feed_10k_counter = Counter(record.get(key) for record in feed_10k_records if record.get(key))

    for category_id in keys:
        share_catalog = _share(catalog_counter[category_id], catalog_total)
        share_feed = _share(feed_counter[category_id], feed_total)
        rows.append(
            {
                "category_id": category_id,
                "category_label": labels.get(category_id),
                "catalog_count": catalog_counter[category_id],
                "feed_100k_count": feed_counter[category_id],
                "feed_10k_count": feed_10k_counter[category_id],
                "intersection_count": overlap_counter[category_id],
                "only_catalog_count": only_catalog_counter[category_id],
                "only_feed100k_count": only_feed_counter[category_id],
                "catalog_share_percent": share_catalog,
                "feed_share_percent": share_feed,
                "share_diff_pp": round(share_feed - share_catalog, 4),
                "share_ratio_feed_over_catalog": _safe_ratio(share_feed, share_catalog),
            }
        )
    rows.sort(key=lambda row: row["feed_100k_count"], reverse=True)
    return {
        "rows": rows[:50],
        "catalog_categories": len(catalog_counter),
        "feed_categories": len(feed_counter),
    }


def _category_name_lookup(
    records: list[dict[str, Any]],
    *,
    key: str,
    name_key: str,
) -> dict[str, str]:
    labels: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        category_id = record.get(key)
        category_name = record.get(name_key)
        if category_id and category_name:
            labels[category_id][category_name] += 1
    return {
        category_id: counter.most_common(1)[0][0]
        for category_id, counter in labels.items()
    }


def _subniche_distribution(records: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        for subniche in record.get("subniches") or []:
            if isinstance(subniche, str) and subniche:
                counter[subniche] += 1
    return dict(counter.most_common(50))


def _split_overlap_groups(
    *,
    left_records: list[dict[str, Any]],
    right_records: list[dict[str, Any]],
    overlap_item_ids: set[str],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "catalog_complete": left_records,
        "feed_complete": right_records,
        "intersection": [
            record for record in left_records if record["item_id"] in overlap_item_ids
        ],
        "catalog_only": [
            record for record in left_records if record["item_id"] not in overlap_item_ids
        ],
        "feed_only": [
            record for record in right_records if record["item_id"] not in overlap_item_ids
        ],
    }


def _attribute_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "rows": len(records),
        "distinct_item_ids": len(_distinct_keys(records, "item_id")),
        "distinct_shop_ids": len(_distinct_keys(records, "shop_id")),
        "price_current": _numeric_summary(record.get("price_current") for record in records),
        "price_reference": _numeric_summary(record.get("price_reference") for record in records),
        "discount_percent": _numeric_summary(record.get("discount_percent") for record in records),
        "item_rating": _numeric_summary(record.get("item_rating") for record in records),
        "shop_rating": _numeric_summary(record.get("shop_rating") for record in records),
        "sales_count": _numeric_summary(record.get("sales_count") for record in records),
        "products_per_shop": _numeric_summary(Counter(
            record["shop_id"] for record in records if record.get("shop_id") is not None
        ).values()),
    }


def _profile_breakdown_for_overlap(
    records: list[dict[str, Any]],
    overlap_item_ids: set[str],
) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        if record["item_id"] in overlap_item_ids and record.get("profile"):
            counter[str(record["profile"])] += 1
    return dict(counter)


def _filter_records_by_item_ids(
    records: list[dict[str, Any]],
    item_ids: set[str],
) -> list[dict[str, Any]]:
    return [record for record in records if record.get("item_id") in item_ids]


def _write_overlap_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fieldnames = [
        "dataset",
        "profile",
        "item_id",
        "shop_id",
        "shop_name",
        "product_name",
        "product_link",
        "price_current",
        "price_reference",
        "discount_percent",
        "sales_count",
        "item_rating",
        "shop_rating",
        "category_id_level_1",
        "category_id_level_2",
        "category_id_level_3",
        "category_name_level_1",
        "category_name_level_2",
        "category_name_level_3",
        "subniches",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "dataset": record.get("dataset"),
                    "profile": record.get("profile"),
                    "item_id": record.get("item_id"),
                    "shop_id": record.get("shop_id"),
                    "shop_name": record.get("shop_name"),
                    "product_name": record.get("product_name"),
                    "product_link": record.get("product_link"),
                    "price_current": _stringify_value(record.get("price_current")),
                    "price_reference": _stringify_value(record.get("price_reference")),
                    "discount_percent": _stringify_value(record.get("discount_percent")),
                    "sales_count": _stringify_value(record.get("sales_count")),
                    "item_rating": _stringify_value(record.get("item_rating")),
                    "shop_rating": _stringify_value(record.get("shop_rating")),
                    "category_id_level_1": record.get("category_id_level_1"),
                    "category_id_level_2": record.get("category_id_level_2"),
                    "category_id_level_3": record.get("category_id_level_3"),
                    "category_name_level_1": record.get("category_name_level_1"),
                    "category_name_level_2": record.get("category_name_level_2"),
                    "category_name_level_3": record.get("category_name_level_3"),
                    "subniches": json.dumps(record.get("subniches"), ensure_ascii=False),
                }
            )


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def _compute_discount_percent(
    *,
    current: Decimal | None,
    reference: Decimal | None,
) -> Decimal | None:
    if current is None or reference is None or reference <= 0 or current > reference:
        return None
    return ((reference - current) / reference) * Decimal("100")


def _parse_json_like_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except ValueError:
        return []
    if isinstance(parsed, list):
        return parsed
    return []


def _category_component(values: list[Any], index: int) -> str | None:
    if index >= len(values):
        return None
    return _normalize_digit_key(values[index])


def _derive_shop_id_from_product_link(product_link: str | None) -> str | None:
    if not product_link:
        return None
    parsed = urlparse(product_link)
    match = re.search(r"/product/(\d+)/(\d+)", parsed.path)
    if not match:
        return None
    return match.group(1)


def _normalize_digit_key(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return digits or None


def _detect_mall_flag(row: dict[str, str]) -> bool | None:
    cb_option = _string_or_none(row.get("cb_option"))
    if cb_option is None:
        return None
    return "mall" in cb_option.lower()


def _detect_official_shop_flag(*, feed_kind: str, row: dict[str, str]) -> bool | None:
    if feed_kind == "feed_100k":
        return True
    return None


def _numeric_summary(values: Iterable[Any]) -> dict[str, Any]:
    normalized: list[Decimal] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, Decimal):
            normalized.append(value)
            continue
        try:
            normalized.append(Decimal(str(value)))
        except (InvalidOperation, ValueError):
            continue
    if not normalized:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p25": None,
            "p75": None,
            "p90": None,
            "p95": None,
            "min": None,
            "max": None,
        }
    values_sorted = sorted(normalized)
    return {
        "count": len(values_sorted),
        "mean": _decimal_to_float(sum(values_sorted) / len(values_sorted)),
        "median": _decimal_to_float(_median_decimal(values_sorted)),
        "p25": _decimal_to_float(_percentile_decimal(values_sorted, 25)),
        "p75": _decimal_to_float(_percentile_decimal(values_sorted, 75)),
        "p90": _decimal_to_float(_percentile_decimal(values_sorted, 90)),
        "p95": _decimal_to_float(_percentile_decimal(values_sorted, 95)),
        "min": _decimal_to_float(values_sorted[0]),
        "max": _decimal_to_float(values_sorted[-1]),
    }


def _percent(overlap: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((overlap / total) * 100, 4)


def _share(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((count / total) * 100, 4)


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _median(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    return float(median(values))


def _percentile(values: Sequence[int], percentile: int) -> float:
    if not values:
        return 0.0
    position = (len(values) - 1) * (percentile / 100)
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    if lower == upper:
        return float(values[lower])
    fraction = position - lower
    return float(values[lower] + (values[upper] - values[lower]) * fraction)


def _median_decimal(values: Sequence[Decimal]) -> Decimal:
    mid = len(values) // 2
    if len(values) % 2 == 1:
        return values[mid]
    return (values[mid - 1] + values[mid]) / Decimal("2")


def _percentile_decimal(values: Sequence[Decimal], percentile: int) -> Decimal:
    position = Decimal(len(values) - 1) * (Decimal(percentile) / Decimal("100"))
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] + (values[upper] - values[lower]) * fraction


def _decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
