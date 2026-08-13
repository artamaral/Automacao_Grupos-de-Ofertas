from __future__ import annotations

from datetime import date
from decimal import Decimal

from ofertas_bot.daily_dispatch_planner import DispatchCandidate, PlannedDispatch
from ofertas_bot.storage.supabase_dispatch_plan_store import SupabaseDispatchPlanStore


def test_replace_day_uses_cursor_executemany_for_batch_insert() -> None:
    execute_calls: list[tuple[str, tuple[object, ...]]] = []
    executemany_calls: list[tuple[str, list[tuple[object, ...]]]] = []

    class FakeResult:
        def fetchone(self) -> dict[str, int]:
            return {"consumed": 0}

    class FakeCursor:
        def __enter__(self) -> FakeCursor:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def executemany(self, sql: str, params_seq: list[tuple[object, ...]]) -> None:
            executemany_calls.append((sql, params_seq))

    class FakeTransaction:
        def __enter__(self) -> FakeTransaction:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    class FakeConnection:
        def transaction(self) -> FakeTransaction:
            return FakeTransaction()

        def execute(self, sql: str, params: tuple[object, ...]) -> FakeResult:
            execute_calls.append((sql, params))
            return FakeResult()

        def cursor(self) -> FakeCursor:
            return FakeCursor()

    store = SupabaseDispatchPlanStore(FakeConnection())  # type: ignore[arg-type]

    candidate = DispatchCandidate(
        profile="feminino",
        marketplace="shopee",
        stable_key="a" * 64,
        item_id=123,
        primary_subniche="vestidos",
        commercial_score=Decimal("10.5"),
        sales_count=99,
        rating=Decimal("4.9"),
    )
    item = PlannedDispatch(
        candidate=candidate,
        selection_bucket="fixed_daily",
        selection_reason="fixed_daily:quota",
        planned_date=date(2026, 8, 13),
        planned_hour=8,
        slot_sequence=1,
        daily_sequence=1,
    )

    store.replace_day(
        profile="feminino",
        marketplace="shopee",
        planned_date=date(2026, 8, 13),
        items=[item],
    )

    assert any("pg_advisory_xact_lock" in sql for sql, _ in execute_calls)
    assert any("delete from offers.daily_dispatch_plan" in sql for sql, _ in execute_calls)
    assert len(executemany_calls) == 1
    insert_sql, insert_params = executemany_calls[0]
    assert "insert into offers.daily_dispatch_plan" in insert_sql
    assert insert_params == [
        (
            "feminino",
            "shopee",
            "a" * 64,
            123,
            "vestidos",
            Decimal("10.5"),
            "fixed_daily",
            "fixed_daily:quota",
            date(2026, 8, 13),
            8,
            1,
            1,
        )
    ]
