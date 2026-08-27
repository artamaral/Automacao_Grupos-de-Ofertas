from pathlib import Path

MIGRATION = Path("supabase/migrations/202608270001_shopee_tracking_clicks_conversions.sql")
WORKFLOW = Path("n8n/workflows/ofertas-mvp-supabase.json")


def test_migration_is_additive_and_keeps_existing_ready_view() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert sql.count("alter table offers.daily_dispatch_plan") == 5
    assert "add column if not exists tracking_sub_ids" in sql
    assert "create view offers.v_daily_dispatch_ready_tracked" in sql
    assert "create or replace view offers.v_daily_dispatch_ready" not in sql
    assert "conversion_record_id uuid primary key" in sql
    assert "conversion_id text not null unique" not in sql
    assert "total_commission" in sql
    assert "when i.item_id = p.item_id then 'direct'" in sql
    assert sql.count("enable row level security") == 6


def test_n8n_only_reads_tracked_ready_surface() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert text.count("offers.v_daily_dispatch_ready_tracked") == 4
    assert "offers.v_daily_dispatch_ready ready" not in text
    assert "/api/sendImage" in text
    assert "/api/sendText" not in text


def test_new_systemd_units_do_not_modify_existing_units() -> None:
    refresh = Path("deploy/systemd/shopee-refresh-plan-tracking.timer").read_text()
    conversion = Path("deploy/systemd/shopee-conversion-report-sync.timer").read_text()
    assert "06:30:00 America/Sao_Paulo" in refresh
    assert "11:00:00 America/Sao_Paulo" in conversion
    assert "Persistent=true" in conversion


def test_conversion_query_has_required_outputs_and_no_product_id() -> None:
    text = Path("src/ofertas_bot/providers/shopee_tracking.py").read_text()
    for field in (
        "clickTime", "purchaseTime", "conversionId", "totalCommission", "netCommission",
        "sellerCommission", "shopeeCommissionCapped", "utmContent", "orderId", "itemId",
        "itemTotalCommission", "attributionType", "scrollId",
    ):
        assert field in text
    assert "productId" not in text
    assert "GenerateShortLink($originUrl: String!" in text
