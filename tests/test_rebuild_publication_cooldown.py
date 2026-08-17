from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.supabase.rebuild_publication_cooldown import is_rebuild_window

BRT = ZoneInfo("America/Sao_Paulo")


def test_rebuild_window_accepts_after_last_dispatch_and_before_planning() -> None:
    assert is_rebuild_window(datetime(2026, 8, 14, 21, 0, tzinfo=BRT))
    assert is_rebuild_window(datetime(2026, 8, 15, 6, 59, tzinfo=BRT))


def test_rebuild_window_rejects_operational_day() -> None:
    assert not is_rebuild_window(datetime(2026, 8, 14, 7, 0, tzinfo=BRT))
    assert not is_rebuild_window(datetime(2026, 8, 14, 20, 59, tzinfo=BRT))
