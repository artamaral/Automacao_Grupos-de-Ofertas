from pathlib import Path


def test_productcatid_migration_preserves_security_and_tracked_ready_contract() -> None:
    sql = (
        Path("supabase/migrations/202608300001_productcatid_catalog.sql")
        .read_text(encoding="utf-8")
        .lower()
    )
    assert "create table if not exists offers.shopee_product_categories" in sql
    assert "create table if not exists offers.profile_product_category_quotas" in sql
    assert "catalog_status in ('current', 'legacy')" in sql
    assert "refresh_required_after" in sql
    assert "catalog_items_subniches_or_product_cat_id_check" in sql
    assert "alter table offers.shopee_product_categories enable row level security" in sql
    assert "with (security_invoker = true)" in sql
    assert "create or replace view offers.v_daily_dispatch_ready_tracked" in sql
    assert "plan.tracking_short_url as offer_link" in sql
    assert "ready.product_cat_id" in sql


def test_productcatid_import_staging_is_inert_and_access_controlled() -> None:
    sql = (
        Path("supabase/migrations/202608300002_productcatid_import_staging.sql")
        .read_text(encoding="utf-8")
        .lower()
    )
    assert "create table if not exists offers.productcatid_import_batches" in sql
    assert "create table if not exists offers.productcatid_import_batch_items" in sql
    assert "alter table offers.productcatid_import_batches enable row level security" in sql
    assert "revoke all on offers.productcatid_import_batches" in sql
    assert "never consumed by ranking, refresh, planner, or n8n" in sql


def test_productcatid_ranking_migration_is_cutover_gated_and_preserves_view_security() -> None:
    sql = (
        Path("supabase/migrations/202608300003_productcatid_ranking_refresh_planner.sql")
        .read_text(encoding="utf-8")
        .lower()
    )
    assert "offers.v_offer_ranking_productcatid_current" in sql
    assert "with (security_invoker = true)" in sql
    assert "item.catalog_status = 'current'" in sql
    assert "ranking.rating >= 4.5" in sql
    assert "rank_product_cat" in sql
    assert "productcatid_exact" in sql
