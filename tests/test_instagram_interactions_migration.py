from pathlib import Path

MIGRATION = Path("supabase/migrations/202608310002_instagram_interactions.sql")


def test_instagram_interactions_migration_creates_isolated_ledgers() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "create table if not exists offers.instagram_comment_events" in sql
    assert "create table if not exists offers.instagram_dm_events" in sql
    assert "publication_event_id uuid references offers.publication_events(publish_id)" in sql
    assert "alter table offers.publication_events" not in sql


def test_instagram_interactions_migration_has_partial_unique_ids_and_indexes() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "on offers.instagram_comment_events (comment_id)" in sql
    assert "on offers.instagram_dm_events (message_id)" in sql
    assert sql.count("where comment_id is not null") == 1
    assert sql.count("where message_id is not null") == 1
    for index in ("user_event_at", "processing_event_at", "media_event_at", "user_reply_event_at"):
        assert index in sql
