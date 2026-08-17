from __future__ import annotations

from pathlib import Path

MIGRATION = Path("supabase/migrations/202608140001_publication_cooldown_2d.sql")
POLICY = Path("config/selection_profiles.toml")


def test_publication_cooldown_migration_projects_confirmed_events() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace function offers.reconcile_offer_publication_state" in sql
    assert "event.delivery_status = 'confirmed'" in sql
    assert "event.sent_at is not null" in sql
    assert "'america/sao_paulo'" in sql
    assert "::date + 3" in sql
    assert "'publication_confirmed'" in sql
    assert "'publication_cooldown_2d'" in sql


def test_publication_cooldown_migration_is_reconstructible_and_scoped() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace function offers.rebuild_offer_publication_state" in sql
    assert "p_profile <> 'feminino' or p_marketplace <> 'shopee'" in sql
    assert "after insert or update or delete" in sql
    assert "publication_events_sync_offer_selection_state" in sql
    assert "offer_selection_state.similarity_status = 'suppressed'" in sql
    assert "revoke all on function offers.sync_offer_publication_state() from public" in sql


def test_publication_cooldown_migration_does_not_run_backfill_on_apply() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "select offers.rebuild_offer_publication_state(" not in sql


def test_feminino_policy_exposes_two_operational_days() -> None:
    policy = POLICY.read_text(encoding="utf-8")

    feminino = policy.split('slug = "feminino"', maxsplit=1)[1].split(
        "[[policies]]", maxsplit=1
    )[0]
    assert "publication_cooldown_operational_days = 2" in feminino
