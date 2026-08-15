from __future__ import annotations

from pathlib import Path

MIGRATION = Path("supabase/migrations/202608150002_offer_media_assets.sql")


def test_offer_media_assets_migration_creates_simple_media_table() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create table if not exists offers.offer_media_assets" in sql
    assert "unique (profile, marketplace, item_id)" in sql
    assert "image_urls jsonb not null default '[]'::jsonb" in sql
    assert "video_url text" in sql
    assert "source text not null default 'shopee_product_html'" in sql
    assert "status in ('valid', 'no_media', 'failed', 'stale')" in sql
    assert "status <> 'valid'" in sql


def test_offer_media_assets_migration_has_operational_indexes_and_rls() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "offer_media_assets_status_idx" in sql
    assert "offer_media_assets_reels_ready_idx" in sql
    assert "offer_media_assets_carousel_ready_idx" in sql
    assert "alter table offers.offer_media_assets enable row level security" in sql
    assert "revoke all on offers.offer_media_assets from anon" in sql
    assert "revoke all on offers.offer_media_assets from authenticated" in sql
    assert "offer_media_assets_set_updated_at" in sql
