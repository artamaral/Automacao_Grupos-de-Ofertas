from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

MIGRATION = Path("supabase/migrations/202608270001_shopee_tracking_clicks_conversions.sql")
CONFIRMATION = "APPLY_SHOPEE_TRACKING_MIGRATION"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-remote-write")
    args = parser.parse_args()
    load_dotenv()
    url = os.getenv("SUPABASE_DB_URL", "").strip()
    if not url:
        raise ValueError("SUPABASE_DB_URL is required")
    checksum = hashlib.sha256(MIGRATION.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    with psycopg.connect(url) as connection:
        existing = connection.execute(
            """select checksum_sha256 from offers.schema_migrations
            where migration_name=%s""", (MIGRATION.name,)
        ).fetchone()
        if existing:
            if existing[0] != checksum:
                raise ValueError("applied migration checksum mismatch")
            print(f"{MIGRATION.name}: applied")
            return 0
        if not args.apply:
            print(f"{MIGRATION.name}: pending")
            return 0
        if args.confirm_remote_write != CONFIRMATION:
            raise ValueError(f"--confirm-remote-write must be {CONFIRMATION}")
        connection.execute("select pg_advisory_xact_lock(hashtext('shopee_tracking_migration'))")
        connection.execute(MIGRATION.read_text(encoding="utf-8"))
        connection.execute(
            """insert into offers.schema_migrations(migration_name,checksum_sha256)
            values (%s,%s)""", (MIGRATION.name, checksum)
        )
    print(f"{MIGRATION.name}: applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
