from pathlib import Path

MIGRATION = Path(
    "supabase/migrations/202609100001_catalog_selection_mode.sql"
)


def test_catalog_selection_mode_migration_defines_constrained_nullable_origin() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "add column if not exists selection_mode text" in sql
    assert "selection_mode in ('productCatId', 'user_defined')" in sql
    assert "catalog_items_current_selection_mode_idx" in sql
    assert "where catalog_status = 'current' and selection_mode is not null" in sql


def test_catalog_selection_mode_migration_backfills_only_proven_origins() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "automatic_current_count <> 4511" in sql
    assert "manual_import_row_count is distinct from 311" in sql
    assert "manual_catalog_item_count <> 311" in sql
    assert "set selection_mode = 'productCatId'" in sql
    assert "selection_mode = 'user_defined'" in sql
    assert "catalog_status = 'current'" in sql
    assert "503a3436-7a36-41fb-9303-1aee43e8d978" in sql


def test_catalog_selection_mode_migration_validates_final_state() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "automatic_count <> 4511" in sql
    assert "manual_count <> 311" in sql
    assert "current_null_count <> 0" in sql
    assert "current_total <> 4822" in sql
    assert "legacy_classified_count <> 0" in sql
