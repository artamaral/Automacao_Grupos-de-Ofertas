from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from psycopg.types.json import Jsonb

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.supabase.import_catalog import (  # noqa: E402
    CatalogImportError,
    connect,
    parse_observed_at,
)

CONFIRMATION = "CUTOVER_PRODUCTCATID_CATALOG"
OPERATIONAL_TZ = ZoneInfo("America/Sao_Paulo")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote an inert productCatId batch.")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--cutover-at", help="ISO 8601 timestamp with timezone.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-remote-write")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(".data/productcatid_cutover_report.json"),
    )
    return parser.parse_args()


def _require_quiet_period(cutover_at: datetime) -> None:
    if cutover_at.astimezone(OPERATIONAL_TZ).hour < 21:
        raise CatalogImportError("cutover requires time at or after 21:00 America/Sao_Paulo")


def preflight(connection, *, batch_id: str, cutover_at: datetime) -> dict[str, object]:
    _require_quiet_period(cutover_at)
    batch = connection.execute(
        """
        select id, profile, marketplace, catalog_generation, source_path, source_sha256,
          source_modified_at, observed_at, row_count
        from offers.productcatid_import_batches where id = %s
        """,
        (batch_id,),
    ).fetchone()
    if batch is None:
        raise CatalogImportError("productCatId batch not found")
    if batch[1] != "feminino" or batch[2] != "shopee":
        raise CatalogImportError("batch must be feminino/shopee")
    stage = connection.execute(
        """
        select count(*), count(distinct product_cat_id),
          count(*) filter (where rating < 4.5 or rating is null)
        from offers.productcatid_import_batch_items where batch_id = %s
        """,
        (batch_id,),
    ).fetchone()
    quota_mismatch = connection.execute(
        """
        with actual as (
          select product_cat_id, count(*) as count
          from offers.productcatid_import_batch_items where batch_id = %s
          group by product_cat_id
        )
        select count(*) from offers.profile_product_category_quotas quota
        full join actual using (product_cat_id)
        where quota.profile = 'feminino' and quota.marketplace = 'shopee' and quota.enabled
          and (actual.count is null or quota.daily_quantity > actual.count)
        """,
        (batch_id,),
    ).fetchone()[0]
    plan = connection.execute(
        """
        select count(*), count(*) filter (where dispatch_status = 'confirmed'),
          count(*) filter (where dispatch_status <> 'confirmed')
        from offers.daily_dispatch_plan
        where profile = 'feminino' and marketplace = 'shopee'
          and planned_date = (%s at time zone 'America/Sao_Paulo')::date
        """,
        (cutover_at,),
    ).fetchone()
    stable_conflicts = connection.execute(
        """
        select count(*) from offers.productcatid_import_batch_items stage
        join offers.catalog_items item
          on item.profile = 'feminino' and item.marketplace = 'shopee'
         and item.stable_key = stage.stable_key and item.item_id <> stage.item_id
        where stage.batch_id = %s
        """,
        (batch_id,),
    ).fetchone()[0]
    if stage[0] != batch[8] or stage[1] != 46 or stage[2] != 0 or quota_mismatch:
        raise CatalogImportError("staged batch does not satisfy the category contract")
    if plan[0] != 140 or plan[1] != 140 or plan[2] != 0:
        raise CatalogImportError("today dispatch plan is not fully confirmed")
    if stable_conflicts:
        raise CatalogImportError("staged stable_key conflicts with another catalog item")
    previous = connection.execute(
        """
        select catalog_status, count(*) from offers.catalog_items
        where profile = 'feminino' and marketplace = 'shopee'
        group by catalog_status order by catalog_status
        """
    ).fetchall()
    return {
        "batch_id": batch_id,
        "generation": batch[3],
        "staged_rows": int(stage[0]),
        "staged_categories": int(stage[1]),
        "today_confirmed_slots": int(plan[1]),
        "previous_catalog_statuses": {str(key): int(value) for key, value in previous},
        "cutover_at": cutover_at.isoformat(),
    }


def apply_cutover(
    connection,
    *,
    batch_id: str,
    cutover_at: datetime,
    report: dict[str, object],
) -> dict[str, object]:
    with connection.transaction():
        connection.execute(
            "select pg_advisory_xact_lock(hashtext(%s))",
            ("productcatid-cutover:feminino:shopee",),
        )
        report = preflight(connection, batch_id=batch_id, cutover_at=cutover_at)
        batch = connection.execute(
            """
            select profile, marketplace, catalog_generation, source_path, source_sha256,
              source_modified_at, observed_at, row_count
            from offers.productcatid_import_batches where id = %s
            """,
            (batch_id,),
        ).fetchone()
        import_id = connection.execute(
            """
            insert into offers.catalog_imports (
              profile, marketplace, source_path, source_sha256, source_modified_at,
              observed_at, row_count, status, validation_summary
            ) values (%s, %s, %s, %s, %s, %s, %s, 'completed', %s) returning id
            """,
            (
                batch[0],
                batch[1],
                batch[3],
                batch[4],
                batch[5],
                batch[6],
                batch[7],
                Jsonb({"productcatid_batch_id": batch_id, "cutover": True}),
            ),
        ).fetchone()[0]
        connection.execute(
            """
            insert into offers.catalog_item_import_history overriding system value
            select item.* from offers.catalog_items item
            where item.profile = 'feminino' and item.marketplace = 'shopee'
            on conflict do nothing
            """
        )
        connection.execute(
            """
            update offers.catalog_items set catalog_status = 'legacy'
            where profile = 'feminino' and marketplace = 'shopee'
            """
        )
        connection.execute(
            """
            insert into offers.catalog_items (
              import_id, profile, marketplace, stable_key, item_id, product_cat_id,
              product_name, product_link, offer_link, image_url, price, reference_price,
              sales_count, rating, shop_type_codes, seller_commission_rate,
              shopee_commission_rate, is_free_shipping, subniches, source_row_number,
              source_payload, catalog_generation, catalog_status, refresh_required_after
            )
            select %s, batch.profile, batch.marketplace, stage.stable_key, stage.item_id,
              stage.product_cat_id, stage.product_name, stage.product_link, stage.offer_link,
              stage.image_url, stage.price, stage.reference_price, stage.sales_count,
              stage.rating, stage.shop_type_codes, stage.seller_commission_rate,
              stage.shopee_commission_rate, false, stage.subniches, stage.source_row_number,
              stage.source_payload, batch.catalog_generation, 'current', %s
            from offers.productcatid_import_batch_items stage
            join offers.productcatid_import_batches batch on batch.id = stage.batch_id
            where stage.batch_id = %s
            on conflict (profile, marketplace, item_id) do update set
              import_id = excluded.import_id, stable_key = excluded.stable_key,
              product_cat_id = excluded.product_cat_id, product_name = excluded.product_name,
              product_link = excluded.product_link, offer_link = excluded.offer_link,
              image_url = excluded.image_url, price = excluded.price,
              reference_price = excluded.reference_price, sales_count = excluded.sales_count,
              rating = excluded.rating, shop_type_codes = excluded.shop_type_codes,
              seller_commission_rate = excluded.seller_commission_rate,
              shopee_commission_rate = excluded.shopee_commission_rate,
              is_free_shipping = excluded.is_free_shipping, subniches = excluded.subniches,
              source_row_number = excluded.source_row_number,
              source_payload = excluded.source_payload,
              catalog_generation = excluded.catalog_generation, catalog_status = 'current',
              refresh_required_after = excluded.refresh_required_after
            """,
            (import_id, cutover_at, batch_id),
        )
        resulting = connection.execute(
            """
            select catalog_status, count(*) from offers.catalog_items
            where profile = 'feminino' and marketplace = 'shopee'
            group by catalog_status order by catalog_status
            """
        ).fetchall()
        run_id = uuid4()
        result = {str(key): int(value) for key, value in resulting}
        connection.execute(
            """
            insert into offers.productcatid_cutover_runs (
              id, batch_id, catalog_generation, cutover_at, previous_catalog_summary,
              resulting_catalog_summary
            ) values (%s, %s, %s, %s, %s, %s)
            """,
            (run_id, batch_id, batch[2], cutover_at, Jsonb(report), Jsonb(result)),
        )
    return report | {"cutover_run_id": str(run_id), "catalog_statuses": result}


def main() -> int:
    args = parse_args()
    cutover_at = parse_observed_at(args.cutover_at) if args.cutover_at else datetime.now(UTC)
    with connect() as connection:
        report = preflight(connection, batch_id=args.batch_id, cutover_at=cutover_at)
        if args.apply:
            if args.confirm_remote_write != CONFIRMATION:
                raise CatalogImportError(f"--confirm-remote-write must be exactly {CONFIRMATION}")
            report = apply_cutover(
                connection,
                batch_id=args.batch_id,
                cutover_at=cutover_at,
                report=report,
            )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"CUTOVER_PREFLIGHT=OK batch={args.batch_id} rows={report['staged_rows']}")
    print(f"REMOTE_WRITE={'OK' if args.apply else 'SKIPPED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
