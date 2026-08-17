from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb


class PublicationEventStoreError(ValueError):
    """Raised when publication event persistence cannot be completed."""


@dataclass(frozen=True)
class PublicationEventUpsert:
    profile: str
    marketplace: str
    stable_key: str
    item_id: int | None
    target: str
    channel_adapter: str
    manifest_item_number: int
    artifact_generated_at: str
    manifest_created_at: str | None
    planned_at: str | None
    sent_at: str
    offer_title: str
    offer_url: str
    offer_price: float | None
    message_text: str
    payload: dict[str, Any]
    delivery_status: str = "confirmed"


class SupabasePublicationEventStore:
    def __init__(self, database_url: str) -> None:
        clean_database_url = database_url.strip()
        if not clean_database_url:
            raise PublicationEventStoreError("SUPABASE_DB_URL is required")
        self._database_url = clean_database_url

    def upsert_confirmed_events(
        self,
        events: tuple[PublicationEventUpsert, ...],
    ) -> tuple[str, ...]:
        if not events:
            return ()

        rows: list[str] = []
        try:
            with psycopg.connect(self._database_url, connect_timeout=15) as connection:
                for event in events:
                    row = connection.execute(
                        """
                        insert into offers.publication_events (
                          profile,
                          marketplace,
                          stable_key,
                          item_id,
                          target,
                          channel_adapter,
                          delivery_status,
                          manifest_item_number,
                          artifact_generated_at,
                          manifest_created_at,
                          planned_at,
                          sent_at,
                          offer_title,
                          offer_url,
                          offer_price,
                          message_text,
                          payload
                        )
                        values (
                          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
                        )
                        on conflict (
                          profile,
                          target,
                          manifest_item_number,
                          artifact_generated_at
                        )
                        do update
                        set marketplace = excluded.marketplace,
                            stable_key = excluded.stable_key,
                            item_id = excluded.item_id,
                            channel_adapter = excluded.channel_adapter,
                            delivery_status = excluded.delivery_status,
                            manifest_created_at = excluded.manifest_created_at,
                            planned_at = excluded.planned_at,
                            sent_at = excluded.sent_at,
                            offer_title = excluded.offer_title,
                            offer_url = excluded.offer_url,
                            offer_price = excluded.offer_price,
                            message_text = excluded.message_text,
                            payload = excluded.payload,
                            updated_at = now()
                        returning publish_id
                        """,
                        (
                            event.profile,
                            event.marketplace,
                            event.stable_key,
                            event.item_id,
                            event.target,
                            event.channel_adapter,
                            event.delivery_status,
                            event.manifest_item_number,
                            event.artifact_generated_at,
                            event.manifest_created_at,
                            event.planned_at,
                            event.sent_at,
                            event.offer_title,
                            event.offer_url,
                            event.offer_price,
                            event.message_text,
                            Jsonb(event.payload),
                        ),
                    ).fetchone()
                    if row is None:
                        raise PublicationEventStoreError(
                            "publication event insert did not return publish_id"
                        )
                    rows.append(str(row[0]))
        except (psycopg.Error, TypeError, ValueError) as error:
            raise PublicationEventStoreError(
                "could not persist publication events in Supabase"
            ) from error
        return tuple(rows)


def build_publication_event_store_from_env() -> SupabasePublicationEventStore | None:
    load_dotenv()
    database_url = os.getenv("SUPABASE_DB_URL", "").strip()
    if not database_url:
        return None
    return SupabasePublicationEventStore(database_url)
