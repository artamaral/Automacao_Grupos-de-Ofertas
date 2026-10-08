from pathlib import Path

MIGRATION = Path(
    "supabase/migrations/202610080001_persist_daily_dispatch_payload.sql"
)
WORKFLOW = Path("n8n/workflows/ofertas-mvp-supabase.json")


def test_migration_persists_complete_dispatch_payload() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    for column in (
        "product_name",
        "source_offer_link",
        "image_url",
        "price",
        "reference_price",
        "sales_count",
        "rating",
        "score_reasons",
        "rank_profile",
        "rank_subniche",
        "refresh_status",
        "last_checked_at",
        "latest_snapshot_id",
    ):
        assert f"add column if not exists {column}" in sql
    assert "daily_dispatch_plan_direct_claim_window_idx" in sql
    assert "where dispatch_status = 'planned'" in sql
    assert "tracking_status = 'ready'" in sql
    assert "refresh_status = 'fresh'" in sql


def test_ready_views_are_lightweight_queue_projections() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace view offers.v_daily_dispatch_ready" in sql
    assert "create or replace view offers.v_daily_dispatch_ready_tracked" in sql
    assert "from offers.v_offer_ranking" not in sql
    assert "from offers.daily_dispatch_plan plan" in sql


def test_n8n_claims_directly_from_persisted_queue() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8").lower()

    assert "from offers.daily_dispatch_plan plan" in workflow
    assert "for update of plan skip locked" in workflow
    assert "plan.tracking_status = 'ready'" in workflow
    assert "plan.refresh_status = 'fresh'" in workflow
    assert "plan.latest_snapshot_id is not null" in workflow
    assert "offers.v_daily_dispatch_ready" not in workflow
    assert "offers.v_offer_ranking" not in workflow
