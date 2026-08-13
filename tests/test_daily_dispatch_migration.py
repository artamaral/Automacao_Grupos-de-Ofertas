from __future__ import annotations

from pathlib import Path

MIGRATION = Path("supabase/migrations/202608130002_daily_dispatch_plan.sql")


def test_daily_dispatch_migration_exposes_safe_operational_view() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create table if not exists offers.daily_dispatch_plan" in sql
    assert "create or replace view offers.v_daily_dispatch_ready" in sql
    assert "with (security_invoker = true)" in sql
    assert "alter table offers.daily_dispatch_plan enable row level security" in sql
    assert "daily_dispatch_plan_ready_window_idx" in sql
    assert "dispatch_status in ('planned', 'claimed', 'confirmed', 'failed', 'cancelled')" in sql


def test_daily_dispatch_migration_links_publication_idempotently() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "add column if not exists dispatch_plan_id uuid" in sql
    assert "publication_events_dispatch_plan_id_idx" in sql
    assert "create or replace function offers.sync_daily_dispatch_status()" in sql
    assert "after insert or update of delivery_status, sent_at" in sql
