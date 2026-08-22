from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


BASELINES = (
    "202608150002_offer_media_assets.sql",
    "202608150003_instagram_media_ready_view.sql",
    "202608160004_instagram_ready_decoupled_from_base_readiness.sql",
    "202608170001_daily_dispatch_operational_freshness.sql",
)
TARGET = "202608220001_instagram_reels_carousel.sql"
CONFIRMATION = "RECONCILE_INSTAGRAM_MIGRATIONS"


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-remote-write")
    args = parser.parse_args()
    if args.apply and args.confirm_remote_write != CONFIRMATION:
        raise ValueError(f"--confirm-remote-write must be {CONFIRMATION}")
    load_dotenv(".env")
    migrations = Path("supabase/migrations")
    with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as connection:
        checks = {
            "offer_media_assets": "select to_regclass('offers.offer_media_assets') is not null",
            "instagram_view": "select count(*) = 29 from information_schema.columns where table_schema='offers' and table_name='v_instagram_dispatch_ready'",
            "instagram_observability": "select count(*) = 3 from information_schema.columns where table_schema='offers' and table_name='v_instagram_dispatch_ready' and column_name in ('refresh_status','is_eligible','ineligibility_reasons')",
            "daily_freshness": "select count(*) = 4 from information_schema.columns where table_schema='offers' and table_name='v_daily_dispatch_ready' and column_name in ('refresh_status','last_checked_at','age_hours','latest_snapshot_id')",
            "instagram_index_absent": "select not exists(select 1 from pg_indexes where schemaname='offers' and indexname='publication_events_instagram_source_format_idx')",
        }
        results = {name: connection.execute(sql).fetchone()[0] for name, sql in checks.items()}
        if not all(results.values()):
            raise ValueError(f"schema preflight failed: {results}")
        if not args.apply:
            print(f"dry_run=true checks={results}")
            return 0
        connection.execute("select pg_advisory_xact_lock(hashtext('ofertas_bot_schema_migrations'))")
        for name in BASELINES:
            connection.execute(
                "insert into offers.schema_migrations (migration_name, checksum_sha256) values (%s, %s) on conflict (migration_name) do nothing",
                (name, checksum(migrations / name)),
            )
        target = migrations / TARGET
        connection.execute(target.read_text(encoding="utf-8"))
        connection.execute(
            "insert into offers.schema_migrations (migration_name, checksum_sha256) values (%s, %s)",
            (TARGET, checksum(target)),
        )
    print("reconciled=4 applied=202608220001_instagram_reels_carousel.sql")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
