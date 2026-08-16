from __future__ import annotations

from pathlib import Path

MIGRATION = Path("supabase/migrations/202608150003_instagram_media_ready_view.sql")
CAPTION_MIGRATION = Path(
    "supabase/migrations/202608160002_instagram_caption_template_order.sql"
)


def test_instagram_media_ready_view_joins_daily_plan_and_media_assets() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace view offers.v_instagram_dispatch_ready" in sql
    assert "with (security_invoker = true)" in sql
    assert "from offers.v_daily_dispatch_ready ready" in sql
    assert "join offers.offer_media_assets media" in sql
    assert "ready.is_ready_for_dispatch" in sql
    assert "media.status = 'valid'" in sql


def test_instagram_media_ready_view_exposes_reels_and_carousel_formats() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "'reels'::text as instagram_format" in sql
    assert "where media.video_url is not null" in sql
    assert "'carousel'::text as instagram_format" in sql
    assert "where jsonb_array_length(media.image_urls) > 0" in sql
    assert "ready.planned_date" in sql
    assert "ready.planned_hour" in sql
    assert "ready.slot_sequence" in sql
    assert "ready.daily_sequence" in sql


def test_instagram_media_ready_caption_includes_offer_link() -> None:
    sql = CAPTION_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace view offers.v_instagram_dispatch_ready" in sql
    assert "'🔥 ' || ready.product_name" in sql
    assert "'💸 r$ ' || ready.price::text" in sql
    assert "'💸 r$ ' || ready.price::text || ' hoje'" not in sql
    assert "'⭐ ' || ready.rating::text || '/5 na shopee'" in sql
    assert "ready.offer_link" in sql
    assert "nullif(btrim(coalesce(ready.offer_link, '')), '')" in sql
