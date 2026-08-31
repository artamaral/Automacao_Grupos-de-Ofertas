from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

from ofertas_bot.catalog_contract import (
    OPERATIONAL_CATALOG_FIELDNAMES,
    project_operational_catalog_row,
)
from ofertas_bot.productcatid_catalog import normalize_product_cat_id

CONFIRMATION = "IMPORT_CURATED_CATALOG"
PROFILE_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CatalogImportError(ValueError):
    """Raised when a curated catalog cannot be safely imported."""


@dataclass(frozen=True)
class CatalogValidation:
    path: Path
    profile: str
    marketplace: str
    source_sha256: str
    source_modified_at: datetime
    row_count: int
    min_rating: Decimal
    max_rating: Decimal
    subniche_count: int

    def summary(self) -> dict[str, object]:
        return {
            "contract": "clean_catalog_productcatid_rating_4_5_plus_v1",
            "import_mode": "incremental_discovery_v1",
            "row_count": self.row_count,
            "min_rating": str(self.min_rating),
            "max_rating": str(self.max_rating),
            "subniche_count": self.subniche_count,
            "empty_subniches": 0,
            "duplicate_item_ids": 0,
            "duplicate_stable_keys": 0,
        }


@dataclass(frozen=True)
class CatalogItem:
    stable_key: str
    item_id: int
    product_cat_id: int | None
    product_name: str
    product_link: str
    offer_link: str | None
    image_url: str | None
    price: Decimal
    reference_price: Decimal | None
    sales_count: int
    rating: Decimal
    shop_type_codes: list[int]
    seller_commission_rate: Decimal | None
    shopee_commission_rate: Decimal | None
    subniches: list[str]
    source_row_number: int
    source_payload: dict[str, object]


@dataclass(frozen=True)
class CatalogImportResult:
    import_id: str
    status: str
    operation: str
    new_items: int
    existing_items: int
    snapshots: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate or import one curated catalog into Supabase."
    )
    parser.add_argument("--profile", required=True)
    parser.add_argument("--catalog-file", type=Path, required=True)
    parser.add_argument("--marketplace", default="shopee")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write to Supabase. Without this flag the command is validation-only.",
    )
    parser.add_argument(
        "--observed-at",
        help=(
            "ISO 8601 timestamp with timezone for the discovery observation. "
            "Required with --apply."
        ),
    )
    parser.add_argument(
        "--confirm-remote-write",
        help=f"Required with --apply. Expected value: {CONFIRMATION}",
    )
    return parser.parse_args()


def connect() -> psycopg.Connection:
    load_dotenv()
    database_url = os.getenv("SUPABASE_DB_URL")
    if not database_url:
        raise CatalogImportError("SUPABASE_DB_URL is required")
    return psycopg.connect(database_url, connect_timeout=15)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_offer_key(marketplace: str, url: str) -> str:
    parts = urlsplit(url.strip())
    normalized_url = urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            "",
            "",
        )
    )
    raw_key = f"{marketplace}|{normalized_url}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def parse_observed_at(value: str | None) -> datetime:
    if not value:
        raise CatalogImportError("--observed-at is required with --apply")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        observed_at = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise CatalogImportError("--observed-at must be a valid ISO 8601 timestamp") from error
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CatalogImportError("--observed-at must include a timezone")
    return observed_at.astimezone(UTC)


def validate_catalog(path: Path, *, profile: str, marketplace: str) -> CatalogValidation:
    if not PROFILE_PATTERN.fullmatch(profile):
        raise CatalogImportError(f"invalid profile slug: {profile}")
    if not path.is_file():
        raise CatalogImportError(f"catalog file not found: {path}")

    item_ids: set[int] = set()
    stable_keys: set[str] = set()
    all_subniches: set[str] = set()
    ratings: list[Decimal] = []
    row_count = 0

    for item in iter_catalog_items(path, marketplace=marketplace):
        row_count += 1
        if item.item_id in item_ids:
            raise CatalogImportError(f"duplicate itemId: {item.item_id}")
        if item.stable_key in stable_keys:
            raise CatalogImportError(
                f"duplicate stable key at source row {item.source_row_number}"
            )
        item_ids.add(item.item_id)
        stable_keys.add(item.stable_key)
        all_subniches.update(item.subniches)
        ratings.append(item.rating)

    if row_count == 0:
        raise CatalogImportError("catalog must contain at least one data row")
    min_rating = min(ratings)
    if min_rating < Decimal("4.5"):
        raise CatalogImportError(f"catalog rating below 4.5: {min_rating}")

    return CatalogValidation(
        path=path,
        profile=profile,
        marketplace=marketplace,
        source_sha256=file_sha256(path),
        source_modified_at=datetime.fromtimestamp(path.stat().st_mtime, tz=UTC),
        row_count=row_count,
        min_rating=min_rating,
        max_rating=max(ratings),
        subniche_count=len(all_subniches),
    )


def iter_catalog_items(path: Path, *, marketplace: str) -> Iterator[CatalogItem]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        # productCatId is mandatory for the new feminino pipeline, but omitted
        # by historical artifacts that remain importable until cutover.
        required_fields = set(OPERATIONAL_CATALOG_FIELDNAMES) - {"productCatId"}
        missing = sorted(required_fields - set(fieldnames))
        if missing:
            raise CatalogImportError(f"catalog fields missing: {missing}")

        for source_row_number, raw_row in enumerate(reader, start=2):
            projected = project_operational_catalog_row(raw_row)
            yield parse_catalog_item(
                projected,
                marketplace=marketplace,
                source_row_number=source_row_number,
            )


def parse_catalog_item(
    row: dict[str, object],
    *,
    marketplace: str,
    source_row_number: int,
) -> CatalogItem:
    item_id = _required_int(row.get("itemId"), "itemId", source_row_number)
    product_name = _required_text(row.get("productName"), "productName", source_row_number)
    product_link = _required_text(row.get("productLink"), "productLink", source_row_number)
    offer_link = _optional_text(row.get("offerLink"))
    identity_url = offer_link or product_link
    price = _required_decimal(row.get("price"), "price", source_row_number)
    if price <= 0:
        raise CatalogImportError(f"price must be positive at source row {source_row_number}")
    reference_price = _optional_decimal(row.get("priceMax"), "priceMax", source_row_number)
    if reference_price is not None and reference_price <= price:
        reference_price = None
    sales_count = _optional_int(row.get("sales"), default=0, field="sales", row=source_row_number)
    rating = _required_decimal(row.get("ratingStar"), "ratingStar", source_row_number)
    shop_type_codes = _int_list(row.get("shopType"), "shopType", source_row_number)
    subniches = _text_list(row.get("subniches"), "subniches", source_row_number)
    product_cat_id = _optional_product_cat_id(row.get("productCatId"), source_row_number)
    if not subniches and product_cat_id is None:
        raise CatalogImportError(f"subniches must not be empty at source row {source_row_number}")

    return CatalogItem(
        stable_key=stable_offer_key(marketplace, identity_url),
        item_id=item_id,
        product_cat_id=product_cat_id,
        product_name=product_name,
        product_link=product_link,
        offer_link=offer_link,
        image_url=_optional_text(row.get("imageUrl")),
        price=price,
        reference_price=reference_price,
        sales_count=sales_count,
        rating=rating,
        shop_type_codes=shop_type_codes,
        seller_commission_rate=_optional_decimal(
            row.get("sellerCommissionRate"),
            "sellerCommissionRate",
            source_row_number,
        ),
        shopee_commission_rate=_optional_decimal(
            row.get("shopeeCommissionRate"),
            "shopeeCommissionRate",
            source_row_number,
        ),
        subniches=subniches,
        source_row_number=source_row_number,
        source_payload=row,
    )


def import_catalog(
    validation: CatalogValidation,
    *,
    observed_at: datetime,
    confirmation: str | None,
) -> CatalogImportResult:
    if confirmation != CONFIRMATION:
        raise CatalogImportError(f"--confirm-remote-write must be exactly {CONFIRMATION}")
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CatalogImportError("observed_at must include a timezone")
    observed_at = observed_at.astimezone(UTC)

    with connect() as connection:
        connection.execute(
            "select pg_advisory_xact_lock(hashtext(%s))",
            (f"catalog-import:{validation.profile}:{validation.marketplace}",),
        )
        existing = connection.execute(
            """
            select id, status, row_count, validation_summary
            from offers.catalog_imports
            where profile = %s
              and marketplace = %s
              and source_sha256 = %s
              and observed_at = %s
            """,
            (
                validation.profile,
                validation.marketplace,
                validation.source_sha256,
                observed_at,
            ),
        ).fetchone()

        if existing is not None:
            import_id, status, recorded_count, summary = existing
            snapshot_count = connection.execute(
                "select count(*) from offers.offer_snapshots where catalog_import_id = %s",
                (import_id,),
            ).fetchone()[0]
            if recorded_count != validation.row_count or snapshot_count != validation.row_count:
                raise CatalogImportError(
                    "existing import snapshot count does not match the validated catalog"
                )
            new_items = int(summary.get("new_items", 0))
            existing_items = int(summary.get("existing_items", 0))
            if new_items + existing_items != validation.row_count:
                raise CatalogImportError("existing import item counts are incomplete")
            return CatalogImportResult(
                import_id=str(import_id),
                status=str(status),
                operation="reused",
                new_items=new_items,
                existing_items=existing_items,
                snapshots=int(snapshot_count),
            )

        import_id = connection.execute(
            """
            insert into offers.catalog_imports (
              profile,
              marketplace,
              source_path,
              source_sha256,
              source_modified_at,
              observed_at,
              row_count,
              status,
              validation_summary
            )
            values (%s, %s, %s, %s, %s, %s, %s, 'completed', %s)
            returning id
            """,
            (
                validation.profile,
                validation.marketplace,
                validation.path.as_posix(),
                validation.source_sha256,
                validation.source_modified_at,
                observed_at,
                validation.row_count,
                Jsonb(validation.summary()),
            ),
        ).fetchone()[0]

        connection.execute(
            """
            create temporary table catalog_import_stage (
              stable_key text not null,
              item_id bigint not null,
              product_cat_id bigint,
              product_name text not null,
              product_link text not null,
              offer_link text,
              image_url text,
              price numeric(14, 2) not null,
              reference_price numeric(14, 2),
              sales_count bigint not null,
              rating numeric(3, 2) not null,
              shop_type_codes smallint[] not null,
              seller_commission_rate numeric(9, 6),
              shopee_commission_rate numeric(9, 6),
              subniches text[] not null,
              source_row_number integer not null,
              source_payload jsonb not null
            ) on commit drop
            """
        )
        copy_sql = """
            copy catalog_import_stage (
              stable_key,
              item_id,
              product_cat_id,
              product_name,
              product_link,
              offer_link,
              image_url,
              price,
              reference_price,
              sales_count,
              rating,
              shop_type_codes,
              seller_commission_rate,
              shopee_commission_rate,
              subniches,
              source_row_number,
              source_payload
            )
            from stdin
        """
        with connection.cursor() as cursor, cursor.copy(copy_sql) as copy:
            for item in iter_catalog_items(
                validation.path,
                marketplace=validation.marketplace,
            ):
                copy.write_row(
                    (
                        item.stable_key,
                        item.item_id,
                        item.product_cat_id,
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
                        item.subniches,
                        item.source_row_number,
                        Jsonb(item.source_payload),
                    )
                )

        stable_key_conflict = connection.execute(
            """
            select stage.source_row_number, stage.stable_key, stage.item_id, item.item_id
            from catalog_import_stage stage
            join offers.catalog_items item
              on item.profile = %s
             and item.marketplace = %s
             and item.stable_key = stage.stable_key
             and item.item_id <> stage.item_id
            limit 1
            """,
            (validation.profile, validation.marketplace),
        ).fetchone()
        if stable_key_conflict is not None:
            source_row, stable_key, incoming_item_id, stored_item_id = stable_key_conflict
            raise CatalogImportError(
                "stable key conflict at source row "
                f"{source_row}: key={stable_key} "
                f"incoming_item_id={incoming_item_id} stored_item_id={stored_item_id}"
            )

        existing_count = connection.execute(
            """
            select count(*)
            from catalog_import_stage stage
            join offers.catalog_items item
              on item.profile = %s
             and item.marketplace = %s
             and item.item_id = stage.item_id
            """,
            (validation.profile, validation.marketplace),
        ).fetchone()[0]

        new_count = connection.execute(
            """
            with inserted as (
              insert into offers.catalog_items (
                import_id,
                profile,
                marketplace,
                stable_key,
                item_id,
                product_cat_id,
                product_name,
                product_link,
                offer_link,
                image_url,
                price,
                reference_price,
                sales_count,
                rating,
                shop_type_codes,
                seller_commission_rate,
                shopee_commission_rate,
                is_free_shipping,
                subniches,
                source_row_number,
                source_payload
              )
              select
                %s,
                %s,
                %s,
                stage.stable_key,
                stage.item_id,
                stage.product_cat_id,
                stage.product_name,
                stage.product_link,
                stage.offer_link,
                stage.image_url,
                stage.price,
                stage.reference_price,
                stage.sales_count,
                stage.rating,
                stage.shop_type_codes,
                stage.seller_commission_rate,
                stage.shopee_commission_rate,
                false,
                stage.subniches,
                stage.source_row_number,
                stage.source_payload
              from catalog_import_stage stage
              on conflict (profile, marketplace, item_id) do nothing
              returning id
            )
            select count(*) from inserted
            """,
            (import_id, validation.profile, validation.marketplace),
        ).fetchone()[0]
        if new_count + existing_count != validation.row_count:
            raise CatalogImportError(
                "catalog classification count mismatch: "
                f"new={new_count} existing={existing_count} rows={validation.row_count}"
            )

        snapshot_count = connection.execute(
            """
            with inserted as (
              insert into offers.offer_snapshots (
                marketplace,
                item_id,
                product_cat_id,
                checked_at,
                product_name,
                product_link,
                offer_link,
                image_url,
                price,
                price_min,
                price_max,
                price_discount_rate,
                commission_rate,
                seller_commission_rate,
                shopee_commission_rate,
                sales_count,
                rating,
                shop_type_codes,
                source,
                source_payload,
                catalog_import_id
              )
              select
                %s,
                stage.item_id,
                stage.product_cat_id,
                %s,
                stage.product_name,
                stage.product_link,
                stage.offer_link,
                stage.image_url,
                stage.price,
                stage.price,
                stage.reference_price,
                case
                  when stage.reference_price > stage.price
                    then round(
                      ((stage.reference_price - stage.price) / stage.reference_price) * 100,
                      3
                    )
                  else null
                end,
                case
                  when stage.seller_commission_rate is not null
                    or stage.shopee_commission_rate is not null
                    then coalesce(stage.seller_commission_rate, 0)
                       + coalesce(stage.shopee_commission_rate, 0)
                  else null
                end,
                stage.seller_commission_rate,
                stage.shopee_commission_rate,
                stage.sales_count,
                stage.rating,
                stage.shop_type_codes,
                'catalog_discovery',
                stage.source_payload,
                %s
              from catalog_import_stage stage
              returning id
            )
            select count(*) from inserted
            """,
            (validation.marketplace, observed_at, import_id),
        ).fetchone()[0]
        if snapshot_count != validation.row_count:
            raise CatalogImportError(
                f"snapshot row count mismatch: {snapshot_count} != {validation.row_count}"
            )

        completed_summary = validation.summary() | {
            "new_items": int(new_count),
            "existing_items": int(existing_count),
            "snapshots": int(snapshot_count),
        }
        connection.execute(
            """
            update offers.catalog_imports
            set validation_summary = %s
            where id = %s
            """,
            (Jsonb(completed_summary), import_id),
        )

    return CatalogImportResult(
        import_id=str(import_id),
        status="completed",
        operation="created",
        new_items=int(new_count),
        existing_items=int(existing_count),
        snapshots=int(snapshot_count),
    )


def _required_text(value: object, field: str, row: int) -> str:
    text = _optional_text(value)
    if text is None:
        raise CatalogImportError(f"{field} is required at source row {row}")
    return text


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required_decimal(value: object, field: str, row: int) -> Decimal:
    parsed = _optional_decimal(value, field, row)
    if parsed is None:
        raise CatalogImportError(f"{field} is required at source row {row}")
    return parsed


def _optional_decimal(value: object, field: str, row: int) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation as error:
        raise CatalogImportError(f"{field} is invalid at source row {row}") from error


def _required_int(value: object, field: str, row: int) -> int:
    parsed = _optional_int(value, default=-1, field=field, row=row)
    if parsed <= 0:
        raise CatalogImportError(f"{field} must be positive at source row {row}")
    return parsed


def _optional_product_cat_id(value: object, row: int) -> int | None:
    if value in (None, ""):
        return None
    try:
        return normalize_product_cat_id(value)
    except ValueError as error:
        raise CatalogImportError(f"productCatId is invalid at source row {row}") from error


def _optional_int(value: object, *, default: int, field: str, row: int) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = Decimal(str(value))
        return int(parsed)
    except (InvalidOperation, ValueError) as error:
        raise CatalogImportError(f"{field} is invalid at source row {row}") from error


def _int_list(value: object, field: str, row: int) -> list[int]:
    values = _list_value(value, field, row)
    try:
        return [int(item) for item in values]
    except (TypeError, ValueError) as error:
        raise CatalogImportError(f"{field} is invalid at source row {row}") from error


def _text_list(value: object, field: str, row: int) -> list[str]:
    values = _list_value(value, field, row)
    return [str(item).strip() for item in values if str(item).strip()]


def _list_value(value: object, field: str, row: int) -> list[object]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as error:
            raise CatalogImportError(f"{field} is invalid at source row {row}") from error
        if isinstance(parsed, list):
            return parsed
    raise CatalogImportError(f"{field} must be an array at source row {row}")


def main() -> int:
    args = parse_args()
    validation = validate_catalog(
        args.catalog_file,
        profile=args.profile,
        marketplace=args.marketplace,
    )
    print(
        "VALIDATION=OK "
        f"profile={validation.profile} "
        f"rows={validation.row_count} "
        f"rating={validation.min_rating}-{validation.max_rating} "
        f"subniches={validation.subniche_count} "
        f"sha256={validation.source_sha256[:12]}..."
    )

    if not args.apply:
        if args.observed_at:
            observed_at = parse_observed_at(args.observed_at)
            print(f"OBSERVED_AT={observed_at.isoformat()}")
        print("REMOTE_WRITE=SKIPPED")
        return 0

    observed_at = parse_observed_at(args.observed_at)
    result = import_catalog(
        validation,
        observed_at=observed_at,
        confirmation=args.confirm_remote_write,
    )
    print(
        "REMOTE_WRITE=OK "
        f"profile={validation.profile} "
        f"import_id={result.import_id} "
        f"status={result.status} "
        f"operation={result.operation} "
        f"new_items={result.new_items} "
        f"existing_items={result.existing_items} "
        f"snapshots={result.snapshots}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
