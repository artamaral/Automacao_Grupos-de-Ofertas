from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

CONFIRMATION = "APPLY_SUPABASE_MIGRATIONS"
DEFAULT_MIGRATIONS_DIR = Path("supabase/migrations")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect or apply versioned Supabase/PostgreSQL migrations."
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=DEFAULT_MIGRATIONS_DIR,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply pending migrations. Without this flag the command is read-only.",
    )
    parser.add_argument(
        "--confirm-remote-write",
        help=f"Required with --apply. Expected value: {CONFIRMATION}",
    )
    return parser.parse_args()


def migration_files(migrations_dir: Path) -> list[Path]:
    if not migrations_dir.is_dir():
        raise ValueError(f"migration directory not found: {migrations_dir}")
    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        raise ValueError(f"no SQL migrations found in: {migrations_dir}")
    return files


def file_checksum(path: Path) -> str:
    return hashlib.sha256(_canonical_migration_bytes(path)).hexdigest()


def legacy_file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checksum_matches(path: Path, recorded_checksum: str) -> bool:
    return recorded_checksum in {
        file_checksum(path),
        legacy_file_checksum(path),
    }


def _canonical_migration_bytes(path: Path) -> bytes:
    content = path.read_bytes()
    return content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def connect() -> psycopg.Connection:
    load_dotenv()
    database_url = os.getenv("SUPABASE_DB_URL")
    if not database_url:
        raise ValueError("SUPABASE_DB_URL is required")
    return psycopg.connect(database_url, connect_timeout=15)


def ensure_migration_history(connection: psycopg.Connection) -> None:
    connection.execute("create schema if not exists offers")
    connection.execute(
        """
        create table if not exists offers.schema_migrations (
          migration_name text primary key,
          checksum_sha256 text not null check (checksum_sha256 ~ '^[0-9a-f]{64}$'),
          applied_at timestamptz not null default now()
        )
        """
    )


def applied_migrations(connection: psycopg.Connection) -> dict[str, str]:
    exists = connection.execute(
        """
        select exists (
          select 1
          from information_schema.tables
          where table_schema = 'offers'
            and table_name = 'schema_migrations'
        )
        """
    ).fetchone()[0]
    if not exists:
        return {}
    rows = connection.execute(
        """
        select migration_name, checksum_sha256
        from offers.schema_migrations
        order by migration_name
        """
    ).fetchall()
    return {name: checksum for name, checksum in rows}


def inspect(files: list[Path]) -> int:
    with connect() as connection:
        applied = applied_migrations(connection)
    pending_count = 0
    for path in files:
        recorded_checksum = applied.get(path.name)
        if recorded_checksum is None:
            status = "pending"
            pending_count += 1
        elif checksum_matches(path, recorded_checksum):
            status = "applied"
        else:
            status = "checksum-mismatch"
        print(f"{path.name}: {status}")
    return pending_count


def apply(files: list[Path], confirmation: str | None) -> int:
    if confirmation != CONFIRMATION:
        raise ValueError(
            f"--confirm-remote-write must be exactly {CONFIRMATION}"
        )

    applied_count = 0
    with connect() as connection:
        connection.execute(
            "select pg_advisory_xact_lock(hashtext('ofertas_bot_schema_migrations'))"
        )
        ensure_migration_history(connection)
        applied = applied_migrations(connection)

        for path in files:
            checksum = file_checksum(path)
            recorded_checksum = applied.get(path.name)
            if recorded_checksum is not None:
                if not checksum_matches(path, recorded_checksum):
                    raise ValueError(
                        f"applied migration checksum changed: {path.name}"
                    )
                print(f"{path.name}: already applied")
                continue

            connection.execute(path.read_text(encoding="utf-8"))
            connection.execute(
                """
                insert into offers.schema_migrations (
                  migration_name,
                  checksum_sha256
                )
                values (%s, %s)
                """,
                (path.name, checksum),
            )
            applied_count += 1
            print(f"{path.name}: applied")

    return applied_count


def main() -> int:
    args = parse_args()
    files = migration_files(args.migrations_dir)
    if args.apply:
        applied_count = apply(files, args.confirm_remote_write)
        print(f"applied_count={applied_count}")
        return 0

    pending_count = inspect(files)
    print(f"pending_count={pending_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
