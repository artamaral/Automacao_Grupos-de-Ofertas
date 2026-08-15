from pathlib import Path

import pytest

from scripts.supabase.apply_migrations import (
    checksum_matches,
    file_checksum,
    legacy_file_checksum,
    migration_files,
)


def test_migration_files_are_sorted_and_limited_to_sql(tmp_path: Path) -> None:
    (tmp_path / "202602020002_second.sql").write_text("select 2;", encoding="utf-8")
    (tmp_path / "202602020001_first.sql").write_text("select 1;", encoding="utf-8")
    (tmp_path / "notes.md").write_text("ignored", encoding="utf-8")

    files = migration_files(tmp_path)

    assert [path.name for path in files] == [
        "202602020001_first.sql",
        "202602020002_second.sql",
    ]


def test_migration_files_requires_at_least_one_sql_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no SQL migrations"):
        migration_files(tmp_path)


def test_file_checksum_is_stable_sha256(tmp_path: Path) -> None:
    migration = tmp_path / "migration.sql"
    migration.write_bytes(b"select 1;\n")

    assert file_checksum(migration) == (
        "4a45092ccf992ea92250053a80b931b787924ba61648f420555511b84f10ab6c"
    )


def test_file_checksum_ignores_line_ending_differences(tmp_path: Path) -> None:
    lf_migration = tmp_path / "lf.sql"
    crlf_migration = tmp_path / "crlf.sql"
    lf_migration.write_bytes(b"select 1;\nselect 2;\n")
    crlf_migration.write_bytes(b"select 1;\r\nselect 2;\r\n")

    assert file_checksum(lf_migration) == file_checksum(crlf_migration)


def test_checksum_matches_legacy_raw_checksum(tmp_path: Path) -> None:
    migration = tmp_path / "migration.sql"
    migration.write_bytes(b"select 1;\r\n")

    recorded_checksum = legacy_file_checksum(migration)

    assert checksum_matches(migration, recorded_checksum)


def test_checksum_matches_legacy_crlf_checksum_from_lf_checkout(tmp_path: Path) -> None:
    migration = tmp_path / "migration.sql"
    migration.write_bytes(b"select 1;\nselect 2;\n")
    crlf_copy = tmp_path / "migration-crlf.sql"
    crlf_copy.write_bytes(b"select 1;\r\nselect 2;\r\n")

    recorded_checksum = legacy_file_checksum(crlf_copy)

    assert checksum_matches(migration, recorded_checksum)
