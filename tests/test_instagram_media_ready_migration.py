from __future__ import annotations

from pathlib import Path

MIGRATION = Path("supabase/migrations/202608150003_instagram_media_ready_view.sql")
CAPTION_MIGRATION = Path(
    "supabase/migrations/202608160002_instagram_caption_template_order.sql"
)
QUEUE_MIGRATION = Path(
    "supabase/migrations/202608160003_instagram_queue_decoupled_from_hour.sql"
)
READINESS_MIGRATION = Path(
    "supabase/migrations/202608160004_instagram_ready_decoupled_from_base_readiness.sql"
)


def test_instagram_media_ready_view_joins_daily_plan_and_media_assets() -> None:
    sql = READINESS_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace view offers.v_instagram_dispatch_ready" in sql
    assert "with (security_invoker = true)" in sql
    assert "from offers.daily_dispatch_plan plan" in sql
    assert "join offers.v_offer_ranking_current ranking" in sql
    assert "join offers.offer_media_assets media" in sql
    assert "plan.dispatch_status = 'planned'" in sql
    assert "media.status = 'valid'" in sql
    assert "ready.is_ready_for_dispatch" not in sql


def test_instagram_media_ready_view_exposes_reels_and_carousel_formats() -> None:
    sql = READINESS_MIGRATION.read_text(encoding="utf-8").lower()

    assert "'reels'::text as instagram_format" in sql
    assert "where media.video_url is not null" in sql
    assert "'carousel'::text as instagram_format" in sql
    assert "where jsonb_array_length(media.image_urls) > 0" in sql
    assert "plan.planned_date" in sql
    assert "plan.planned_hour" in sql
    assert "plan.slot_sequence" in sql
    assert "plan.daily_sequence" in sql


def test_instagram_media_ready_view_exposes_ranking_observability_without_blocking() -> None:
    sql = READINESS_MIGRATION.read_text(encoding="utf-8").lower()

    assert "ranking.refresh_status" in sql
    assert "ranking.is_eligible" in sql
    assert "ranking.ineligibility_reasons" in sql


def test_instagram_media_ready_caption_includes_offer_link() -> None:
    sql = CAPTION_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace view offers.v_instagram_dispatch_ready" in sql
    assert "'🔥 ' || ready.product_name" in sql
    assert "'💸 r$ ' || ready.price::text" in sql
    assert "'💸 r$ ' || ready.price::text || ' hoje'" not in sql
    assert "'⭐ ' || ready.rating::text || '/5 na shopee'" in sql
    assert "ready.offer_link" in sql
    assert "nullif(btrim(coalesce(ready.offer_link, '')), '')" in sql


def test_instagram_queue_uses_daily_sequence_over_planned_hour() -> None:
    sql = QUEUE_MIGRATION.read_text(encoding="utf-8").lower()

    assert "ready.planned_hour" in sql
    assert "planned_hour permanece apenas como auditoria" in sql
    assert "order by" in sql
    assert "ready.planned_date," in sql
    assert "ready.daily_sequence," in sql
    assert "format.instagram_format desc" in sql
