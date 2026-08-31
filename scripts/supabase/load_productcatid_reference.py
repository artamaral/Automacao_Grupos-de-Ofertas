from __future__ import annotations

import argparse
import csv
import hashlib
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from ofertas_bot.productcatid_catalog import (
    load_product_category_quotas,
    validate_quotas_against_category_csv,
)

CONFIRMATION = "LOAD_PRODUCTCATID_REFERENCE"


def connect() -> psycopg.Connection:
    load_dotenv()
    database_url = os.getenv("SUPABASE_DB_URL")
    if not database_url:
        raise RuntimeError("SUPABASE_DB_URL is required")
    return psycopg.connect(database_url, connect_timeout=15)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load Shopee categories and feminino quotas."
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-remote-write")
    parser.add_argument(
        "--categories", type=Path, default=Path("data/shopee_product_categories.csv")
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        default=Path("config/shopee_productcatid_quotas_feminino.csv"),
    )
    args = parser.parse_args()
    quotas = load_product_category_quotas(args.matrix)
    validate_quotas_against_category_csv(quotas, args.categories)
    categories = _read_categories(args.categories)
    total_quota = sum(item.daily_quantity for item in quotas)
    print(
        "REFERENCE_VALID=OK "
        f"categories={len(categories)} quotas={len(quotas)} total={total_quota}"
    )
    if not args.apply:
        print("REMOTE_WRITE=SKIPPED")
        return 0
    if args.confirm_remote_write != CONFIRMATION:
        raise SystemExit(f"--confirm-remote-write must be exactly {CONFIRMATION}")
    source_sha256 = _sha256(args.categories)
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """create temporary table productcatid_category_stage (
                    category_id bigint, category text, sub_category text, level_3 text,
                    level_4 text, level_5 text, category_path text, source_sha256 text
                ) on commit drop"""
            )
            with cursor.copy(
                "copy productcatid_category_stage from stdin"
            ) as copy:
                for row in categories:
                    copy.write_row(
                        (
                            row["category_id"],
                            row["category"],
                            row["sub_category"],
                            row["level_3"],
                            row["level_4"],
                            row["level_5"],
                            row["category_path"],
                            source_sha256,
                        )
                    )
            cursor.execute(
                """insert into offers.shopee_product_categories (
                    category_id, category, sub_category, level_3, level_4,
                    level_5, category_path, source_sha256
                )
                    select category_id, category, sub_category, level_3, level_4,
                      level_5, category_path, source_sha256
                    from productcatid_category_stage
                    on conflict (category_id) do update set
                      category = excluded.category,
                      sub_category = excluded.sub_category,
                      level_3 = excluded.level_3,
                      level_4 = excluded.level_4,
                      level_5 = excluded.level_5,
                      category_path = excluded.category_path,
                      source_sha256 = excluded.source_sha256,
                      loaded_at = now()"""
            )
            cursor.executemany(
                """insert into offers.profile_product_category_quotas
                    (profile, marketplace, product_cat_id, daily_quantity, enabled, source_sha256)
                    values ('feminino', 'shopee', %s, %s, true, %s)
                    on conflict (profile, marketplace, product_cat_id) do update set
                      daily_quantity=excluded.daily_quantity, enabled=true,
                      source_sha256=excluded.source_sha256, updated_at=now()""",
                [
                    (quota.product_cat_id, quota.daily_quantity, source_sha256)
                    for quota in quotas
                ],
            )
    print("REMOTE_WRITE=OK")
    return 0


def _read_categories(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = []
    for row in rows:
        keys = ("category", "sub_category", "level_3", "level_4", "level_5")
        path_parts = [row.get(key, "").strip() for key in keys]
        result.append(
            {
                "category_id": int(row["category_id"]),
                "category": row["category"].strip(),
                "sub_category": row.get("sub_category") or None,
                "level_3": row.get("level_3") or None,
                "level_4": row.get("level_4") or None,
                "level_5": row.get("level_5") or None,
                "category_path": " > ".join(part for part in path_parts if part),
            }
        )
    return result


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
