from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path


TARGET_PROFILE = "quality_floor_legacy"
SOURCE_PROFILE = "feminino"
MARKETPLACE = "shopee"
CONFIRMATION = "APPLY_QUALITY_FLOOR_LEGACY"
REQUIRED_COLUMNS = {"item_id", "target_profile"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Apply the quality-floor legacy inactivation list to offers.catalog_items. "
            "Default mode is dry-run."
        )
    )
    p.add_argument("--csv", type=Path, required=True, help="Candidate CSV to load.")
    p.add_argument(
        "--export-current-list",
        type=Path,
        help=(
            "Write an exact CSV containing only candidate rows that currently have "
            "profile='feminino' in Supabase. No update is performed unless --apply is also set."
        ),
    )
    p.add_argument("--apply", action="store_true", help="Perform the UPDATE. Default is dry-run.")
    p.add_argument(
        "--confirm-remote-write",
        help=f"Required with --apply. Must be exactly: {CONFIRMATION}",
    )
    p.add_argument(
        "--expected-count",
        type=int,
        help="Optional safety check: fail if the current matching row count differs.",
    )
    return p.parse_args()


def connect():
    try:
        import psycopg
        from dotenv import load_dotenv
    except ImportError as exc:
        raise SystemExit("Dependencies missing. Install project dependencies (psycopg, python-dotenv).") from exc
    load_dotenv()
    database_url = os.getenv("SUPABASE_DB_URL")
    if not database_url:
        raise SystemExit("SUPABASE_DB_URL is required")
    return psycopg.connect(database_url, connect_timeout=15)


def read_candidates(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"CSV not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - fields)
        if missing:
            raise SystemExit(f"CSV missing required columns: {missing}")
        rows = list(reader)

    seen: set[int] = set()
    for i, row in enumerate(rows, start=2):
        try:
            item_id = int(row["item_id"])
        except Exception as exc:
            raise SystemExit(f"Invalid item_id at CSV row {i}: {row.get('item_id')!r}") from exc
        if item_id in seen:
            raise SystemExit(f"Duplicate item_id in CSV: {item_id}")
        seen.add(item_id)
        if row["target_profile"] != TARGET_PROFILE:
            raise SystemExit(
                f"Unexpected target_profile at CSV row {i}: {row['target_profile']!r}; "
                f"expected {TARGET_PROFILE!r}"
            )
    return rows


def export_current(path: Path, fieldnames: list[str], rows: list[dict[str, str]], current_ids: set[int]) -> int:
    selected = [r for r in rows if int(r["item_id"]) in current_ids]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(selected)
    return len(selected)


def main() -> int:
    args = parse_args()
    rows = read_candidates(args.csv)
    candidate_ids = [int(r["item_id"]) for r in rows]
    fieldnames = list(rows[0].keys()) if rows else ["item_id", "target_profile"]

    if args.apply and args.confirm_remote_write != CONFIRMATION:
        raise SystemExit(f"--confirm-remote-write must be exactly {CONFIRMATION}")

    with connect() as conn:
        # Serialize this operation for the target profile/marketplace.
        conn.execute(
            "select pg_advisory_xact_lock(hashtext(%s))",
            (f"quality-floor-legacy:{SOURCE_PROFILE}:{MARKETPLACE}",),
        )
        conn.execute("create temporary table quality_floor_ids (item_id bigint primary key) on commit drop")
        with conn.cursor() as cur, cur.copy("copy quality_floor_ids (item_id) from stdin") as copy:
            for item_id in candidate_ids:
                copy.write_row((item_id,))

        current_rows = conn.execute(
            """
            select c.item_id
            from offers.catalog_items c
            join quality_floor_ids q using (item_id)
            where c.marketplace = %s
              and c.profile = %s
            order by c.item_id
            """,
            (MARKETPLACE, SOURCE_PROFILE),
        ).fetchall()
        current_ids = {int(r[0]) for r in current_rows}
        current_count = len(current_ids)
        skipped_count = len(candidate_ids) - current_count

        print(f"csv_candidates={len(candidate_ids)}")
        print(f"current_feminino_matches={current_count}")
        print(f"already_not_feminino_or_missing={skipped_count}")

        if args.expected_count is not None and current_count != args.expected_count:
            raise SystemExit(
                f"Safety check failed: expected {args.expected_count} current matches, got {current_count}"
            )

        if args.export_current_list:
            n = export_current(args.export_current_list, fieldnames, rows, current_ids)
            print(f"exported_current_list={n} path={args.export_current_list}")

        if not args.apply:
            conn.rollback()
            print("dry_run=true; no database rows changed")
            return 0

        updated = conn.execute(
            """
            update offers.catalog_items c
               set profile = %s
              from quality_floor_ids q
             where c.item_id = q.item_id
               and c.marketplace = %s
               and c.profile = %s
            returning c.item_id
            """,
            (TARGET_PROFILE, MARKETPLACE, SOURCE_PROFILE),
        ).fetchall()
        updated_ids = {int(r[0]) for r in updated}

        if updated_ids != current_ids:
            missing = sorted(current_ids - updated_ids)[:20]
            unexpected = sorted(updated_ids - current_ids)[:20]
            raise RuntimeError(
                f"Update verification failed; missing={missing} unexpected={unexpected}"
            )

        remaining = conn.execute(
            """
            select count(*)
            from offers.catalog_items c
            join quality_floor_ids q using (item_id)
            where c.marketplace = %s
              and c.profile = %s
            """,
            (MARKETPLACE, SOURCE_PROFILE),
        ).fetchone()[0]
        if remaining != 0:
            raise RuntimeError(f"Post-update verification failed: {remaining} matching rows still feminino")

        conn.commit()
        print(f"updated={len(updated_ids)} target_profile={TARGET_PROFILE}")
        print("verification=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
