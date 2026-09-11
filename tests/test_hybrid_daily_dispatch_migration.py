from __future__ import annotations

from pathlib import Path

MIGRATION = Path(
    "supabase/migrations/202609100002_hybrid_daily_dispatch_selection_mode.sql"
)


def test_hybrid_migration_sets_13_categories_and_78_slots() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "enabled_categories <> 13" in sql
    assert "enabled_slots <> 78" in sql
    assert "set enabled = false" in sql
    assert "user_defined_rank" in sql


def test_hybrid_migration_preserves_selection_mode_in_cutover_history() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "offers.catalog_item_import_history" in sql
    assert "add column if not exists selection_mode text" in sql


def test_productcatid_cutover_sets_origin_only_on_insert() -> None:
    source = Path("scripts/supabase/cutover_productcatid_catalog.py").read_text(
        encoding="utf-8"
    )
    update_clause = source.split(
        "on conflict (profile, marketplace, item_id) do update set", maxsplit=1
    )[1].split('""",', maxsplit=1)[0]

    assert "'productCatId'" in source
    assert "selection_mode" not in update_clause
