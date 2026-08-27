from __future__ import annotations

import os
from datetime import date
from uuid import UUID

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

from ofertas_bot.shopee_tracking import TrackingPlan


class SupabaseShopeeTrackingStore:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

    @classmethod
    def connect_from_env(cls) -> SupabaseShopeeTrackingStore:
        load_dotenv()
        url = os.getenv("SUPABASE_DB_URL", "").strip()
        if not url:
            raise ValueError("SUPABASE_DB_URL is required")
        return cls(psycopg.connect(url, autocommit=True, row_factory=dict_row))

    def close(self) -> None:
        self.connection.close()

    def pending_plans(self, profile: str, planned_date: date) -> list[TrackingPlan]:
        rows = self.connection.execute(
            """
            select p.dispatch_plan_id, p.profile, p.item_id, c.product_link
            from offers.daily_dispatch_plan p
            join lateral (
              select product_link from offers.catalog_items c
              where c.profile=p.profile and c.marketplace=p.marketplace
                and c.stable_key=p.stable_key
              order by c.created_at desc limit 1
            ) c on true
            where p.profile=%s and p.marketplace='shopee' and p.planned_date=%s
              and p.dispatch_status='planned' and p.tracking_status <> 'ready'
            order by p.daily_sequence
            """,
            (profile, planned_date),
        ).fetchall()
        return [TrackingPlan(UUID(str(r["dispatch_plan_id"])), str(r["profile"]),
                             int(r["item_id"]), str(r["product_link"] or "")) for r in rows]

    def save_ready(self, dispatch_plan_id: UUID, sub_ids: tuple[str, ...], url: str) -> None:
        self.connection.execute(
            """update offers.daily_dispatch_plan set tracking_sub_ids=%s,
            tracking_short_url=%s, tracking_generated_at=now(), tracking_status='ready',
            tracking_error=null, updated_at=now() where dispatch_plan_id=%s""",
            (list(sub_ids), url, dispatch_plan_id),
        )

    def save_failed(self, dispatch_plan_id: UUID, error: str) -> None:
        self.connection.execute(
            """update offers.daily_dispatch_plan set tracking_status='failed',
            tracking_error=%s, tracking_generated_at=now(), updated_at=now()
            where dispatch_plan_id=%s""",
            (error[:2000], dispatch_plan_id),
        )

    def lookup_plan(self, dispatch_plan_id: UUID) -> dict[str, object] | None:
        return self.connection.execute(
            """select dispatch_plan_id, profile, item_id from offers.daily_dispatch_plan
            where dispatch_plan_id=%s""", (dispatch_plan_id,)
        ).fetchone()
