from ofertas_bot.storage.supabase_publication_event_store import (
    PublicationEventUpsert,
    SupabasePublicationEventStore,
    build_publication_event_store_from_env,
)


def test_build_publication_event_store_from_env_returns_none_without_url(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.setattr(
        "ofertas_bot.storage.supabase_publication_event_store.load_dotenv",
        lambda: None,
    )

    store = build_publication_event_store_from_env()

    assert store is None


def test_supabase_publication_event_store_upserts_confirmed_events(monkeypatch) -> None:
    execute_calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeResult:
        def __init__(self, value: str) -> None:
            self._value = value

        def fetchone(self) -> tuple[str]:
            return (self._value,)

    class FakeConnection:
        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def execute(self, sql: str, params: tuple[object, ...]) -> FakeResult:
            execute_calls.append((sql, params))
            return FakeResult("pub-1")

    monkeypatch.setattr(
        "ofertas_bot.storage.supabase_publication_event_store.psycopg.connect",
        lambda database_url, connect_timeout: FakeConnection(),
    )

    store = SupabasePublicationEventStore("postgresql://example")
    publish_ids = store.upsert_confirmed_events(
        (
            PublicationEventUpsert(
                profile="feminino",
                marketplace="shopee",
                stable_key="a" * 64,
                item_id=123,
                target="grupo-teste",
                channel_adapter="whatsapp",
                manifest_item_number=1,
                artifact_generated_at="2026-06-29T10:00:00+00:00",
                manifest_created_at="2026-06-29T09:59:00+00:00",
                planned_at="2026-06-29T10:01:00+00:00",
                sent_at="2026-06-29T10:02:00+00:00",
                offer_title="Produto teste",
                offer_url="https://example.com/oferta",
                offer_price=19.9,
                message_text="Oferta teste",
                payload={"source": "cloud_runner.confirm_window_deliveries"},
            ),
        )
    )

    assert publish_ids == ("pub-1",)
    assert len(execute_calls) == 1
    assert "insert into offers.publication_events" in execute_calls[0][0]
    assert execute_calls[0][1][0] == "feminino"
    assert execute_calls[0][1][4] == "grupo-teste"
