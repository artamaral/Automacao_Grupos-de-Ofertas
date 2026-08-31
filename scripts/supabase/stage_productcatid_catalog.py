from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from psycopg.types.json import Jsonb

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ofertas_bot.productcatid_catalog import (  # noqa: E402
    load_product_category_quotas,
    validate_quotas_against_category_csv,
)
from scripts.supabase.import_catalog import (  # noqa: E402
    CatalogImportError,
    CatalogValidation,
    connect,
    iter_catalog_items,
    parse_observed_at,
    validate_catalog,
)

CONFIRMATION = "STAGE_PRODUCTCATID_CATALOG"


@dataclass(frozen=True)
class ProductCatIdStageValidation:
    catalog: CatalogValidation
    catalog_generation: str
    category_count: int
    category_rows: dict[int, int]

    def summary(self) -> dict[str, object]:
        return self.catalog.summary() | {
            "catalog_generation": self.catalog_generation,
            "category_count": self.category_count,
            "category_rows": self.category_rows,
            "operation": "productcatid_pre_cutover_stage_v1",
        }


@dataclass(frozen=True)
class ProductCatIdStageResult:
    batch_id: str
    operation: str
    rows: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate or stage the inert feminino productCatId catalog."
    )
    parser.add_argument("--catalog-file", type=Path, required=True)
    parser.add_argument("--catalog-generation", required=True)
    parser.add_argument(
        "--matrix", type=Path, default=Path("config/shopee_productcatid_quotas_feminino.csv")
    )
    parser.add_argument(
        "--categories", type=Path, default=Path("data/shopee_product_categories.csv")
    )
    parser.add_argument("--observed-at", help="ISO 8601 timestamp with timezone.")
    parser.add_argument("--apply", action="store_true", help="Write only to inert staging tables.")
    parser.add_argument(
        "--confirm-remote-write",
        help=f"Required with --apply. Expected value: {CONFIRMATION}",
    )
    return parser.parse_args()


def validate_productcatid_stage(
    path: Path,
    *,
    catalog_generation: str,
    matrix_path: Path,
    categories_path: Path,
) -> ProductCatIdStageValidation:
    generation = catalog_generation.strip()
    if not generation:
        raise CatalogImportError("catalog_generation is required")

    quotas = load_product_category_quotas(matrix_path)
    validate_quotas_against_category_csv(quotas, categories_path)
    allowed_ids = {quota.product_cat_id for quota in quotas}
    catalog = validate_catalog(path, profile="feminino", marketplace="shopee")
    categories = Counter()
    for item in iter_catalog_items(path, marketplace="shopee"):
        if item.product_cat_id is None:
            raise CatalogImportError(
                f"productCatId is required at source row {item.source_row_number}"
            )
        if item.product_cat_id not in allowed_ids:
            raise CatalogImportError(
                "productCatId outside the active feminino matrix at source row "
                f"{item.source_row_number}: {item.product_cat_id}"
            )
        categories[item.product_cat_id] += 1
    if set(categories) != allowed_ids:
        missing = sorted(allowed_ids - set(categories))
        raise CatalogImportError(f"matrix categories without staged candidates: {missing}")
    return ProductCatIdStageValidation(
        catalog=catalog,
        catalog_generation=generation,
        category_count=len(categories),
        category_rows=dict(sorted(categories.items())),
    )


def stage_productcatid_catalog(
    validation: ProductCatIdStageValidation,
    *,
    observed_at: datetime,
    confirmation: str | None,
) -> ProductCatIdStageResult:
    if confirmation != CONFIRMATION:
        raise CatalogImportError(f"--confirm-remote-write must be exactly {CONFIRMATION}")
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CatalogImportError("observed_at must include a timezone")
    observed_at = observed_at.astimezone(UTC)
    catalog = validation.catalog

    with connect() as connection:
        connection.execute(
            "select pg_advisory_xact_lock(hashtext(%s))",
            (f"productcatid-stage:{catalog.profile}:{catalog.marketplace}",),
        )
        existing = connection.execute(
            """
            select id, source_sha256, row_count
            from offers.productcatid_import_batches
            where profile = %s and marketplace = %s and catalog_generation = %s
            """,
            (catalog.profile, catalog.marketplace, validation.catalog_generation),
        ).fetchone()
        if existing is not None:
            batch_id, source_sha256, row_count = existing
            if source_sha256 != catalog.source_sha256 or row_count != catalog.row_count:
                raise CatalogImportError(
                    "catalog_generation already exists with a different validated source"
                )
            staged_rows = connection.execute(
                "select count(*) from offers.productcatid_import_batch_items where batch_id = %s",
                (batch_id,),
            ).fetchone()[0]
            if staged_rows != catalog.row_count:
                raise CatalogImportError("existing staged batch row count does not match source")
            return ProductCatIdStageResult(str(batch_id), "reused", int(staged_rows))

        batch_id = uuid4()
        connection.execute(
            """
            insert into offers.productcatid_import_batches (
              id, profile, marketplace, catalog_generation, source_path,
              source_sha256, source_modified_at, observed_at, row_count, validation_summary
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                batch_id, catalog.profile, catalog.marketplace, validation.catalog_generation,
                catalog.path.as_posix(), catalog.source_sha256, catalog.source_modified_at,
                observed_at, catalog.row_count, Jsonb(validation.summary()),
            ),
        )
        connection.execute(
            """
            create temporary table productcatid_import_stage (
              stable_key text not null, item_id bigint not null, product_cat_id bigint not null,
              product_name text not null, product_link text not null, offer_link text,
              image_url text, price numeric(14, 2) not null, reference_price numeric(14, 2),
              sales_count bigint not null,
              rating numeric(3, 2) not null, shop_type_codes smallint[] not null,
              seller_commission_rate numeric(9, 6), shopee_commission_rate numeric(9, 6),
              subniches text[] not null, source_row_number integer not null,
              source_payload jsonb not null
            ) on commit drop
            """
        )
        copy_sql = """
            copy productcatid_import_stage (
              stable_key, item_id, product_cat_id, product_name, product_link, offer_link,
              image_url,
              price, reference_price, sales_count, rating, shop_type_codes, seller_commission_rate,
              shopee_commission_rate, subniches, source_row_number, source_payload
            ) from stdin
        """
        with connection.cursor() as cursor, cursor.copy(copy_sql) as copy:
            for item in iter_catalog_items(catalog.path, marketplace=catalog.marketplace):
                copy.write_row(
                    (
                        item.stable_key, item.item_id, item.product_cat_id, item.product_name,
                        item.product_link, item.offer_link, item.image_url, item.price,
                        item.reference_price, item.sales_count, item.rating, item.shop_type_codes,
                        item.seller_commission_rate, item.shopee_commission_rate, item.subniches,
                        item.source_row_number, Jsonb(item.source_payload),
                    )
                )
        inserted_rows = connection.execute(
            """
            with inserted as (
              insert into offers.productcatid_import_batch_items (
                batch_id, stable_key, item_id, product_cat_id, product_name, product_link,
                offer_link,
                image_url, price, reference_price, sales_count, rating, shop_type_codes,
                seller_commission_rate, shopee_commission_rate, subniches, source_row_number,
                source_payload
              )
              select %s, stable_key, item_id, product_cat_id, product_name, product_link,
                offer_link,
                image_url, price, reference_price, sales_count, rating, shop_type_codes,
                seller_commission_rate, shopee_commission_rate, subniches, source_row_number,
                source_payload
              from productcatid_import_stage
              returning item_id
            ) select count(*) from inserted
            """,
            (batch_id,),
        ).fetchone()[0]
        if inserted_rows != catalog.row_count:
            raise CatalogImportError(
                f"staged row count mismatch: {inserted_rows} != {catalog.row_count}"
            )
    return ProductCatIdStageResult(str(batch_id), "created", int(inserted_rows))


def main() -> int:
    args = parse_args()
    validation = validate_productcatid_stage(
        args.catalog_file,
        catalog_generation=args.catalog_generation,
        matrix_path=args.matrix,
        categories_path=args.categories,
    )
    print(
        "PRODUCTCATID_STAGE_VALIDATION=OK "
        f"generation={validation.catalog_generation} rows={validation.catalog.row_count} "
        f"categories={validation.category_count}"
    )
    if not args.apply:
        print("REMOTE_WRITE=SKIPPED")
        return 0
    result = stage_productcatid_catalog(
        validation,
        observed_at=parse_observed_at(args.observed_at),
        confirmation=args.confirm_remote_write,
    )
    print(
        "PRODUCTCATID_STAGE=OK "
        f"batch_id={result.batch_id} operation={result.operation} rows={result.rows}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
