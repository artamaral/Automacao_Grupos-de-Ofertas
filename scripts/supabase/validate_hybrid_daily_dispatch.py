from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    database_url = os.getenv("SUPABASE_DB_URL", "").strip()
    if not database_url:
        raise ValueError("SUPABASE_DB_URL is required")

    with psycopg.connect(database_url, connect_timeout=15) as connection:
        quota_count, quota_slots = connection.execute(
            """
            select count(*), coalesce(sum(daily_quantity), 0)
            from offers.profile_product_category_quotas
            where profile = 'feminino' and marketplace = 'shopee' and enabled
            """
        ).fetchone()
        modes = dict(
            connection.execute(
                """
                select selection_mode, count(*)
                from offers.catalog_items
                where profile = 'feminino'
                  and marketplace = 'shopee'
                  and catalog_status = 'current'
                group by selection_mode
                """
            ).fetchall()
        )
        constraint = connection.execute(
            """
            select pg_get_constraintdef(oid)
            from pg_constraint
            where conrelid = 'offers.daily_dispatch_plan'::regclass
              and conname = 'daily_dispatch_plan_selection_bucket_check'
            """
        ).fetchone()
        migration_count = connection.execute(
            """
            select count(*)
            from offers.schema_migrations
            where migration_name =
              '202609100002_hybrid_daily_dispatch_selection_mode.sql'
            """
        ).fetchone()[0]
        operational_date = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
        plan_total, plan_consumed = connection.execute(
            """
            select count(*), count(*) filter (where dispatch_status <> 'planned')
            from offers.daily_dispatch_plan
            where profile = 'feminino'
              and marketplace = 'shopee'
              and planned_date = %s
            """,
            (operational_date,),
        ).fetchone()

    expected_modes = {"productCatId": 4511, "user_defined": 311}
    if (quota_count, quota_slots) != (13, 78):
        raise RuntimeError(
            f"invalid enabled quotas: categories={quota_count} slots={quota_slots}"
        )
    if modes != expected_modes:
        raise RuntimeError(f"invalid current selection modes: {modes}")
    if constraint is None or "user_defined_rank" not in constraint[0]:
        raise RuntimeError("daily dispatch bucket constraint is not hybrid")
    if migration_count != 1:
        raise RuntimeError("hybrid migration is not recorded exactly once")

    print(
        "HYBRID_DISPATCH=OK "
        f"categories={quota_count} productcatid_slots={quota_slots} "
        f"user_defined_slots={140 - quota_slots} "
        f"productCatId_items={modes['productCatId']} "
        f"user_defined_items={modes['user_defined']} "
        f"today_plan={plan_total} today_consumed={plan_consumed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
