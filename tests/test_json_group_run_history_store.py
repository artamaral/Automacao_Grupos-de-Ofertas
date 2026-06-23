from datetime import UTC, datetime

import pytest

from ofertas_bot.storage.json_group_run_history_store import (
    GroupRunHistoryStoreError,
    JsonGroupRunHistoryStore,
)


def test_json_group_run_history_store_saves_and_loads(tmp_path) -> None:
    path = tmp_path / "history.json"
    now = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    store = JsonGroupRunHistoryStore(path=path)

    store.save({"Maquiagem-VIP": now, "casa-vip": None})

    assert store.load() == {"maquiagem-vip": now, "casa-vip": None}


def test_json_group_run_history_store_returns_empty_when_missing(tmp_path) -> None:
    store = JsonGroupRunHistoryStore(path=tmp_path / "missing.json")

    assert store.load() == {}


def test_json_group_run_history_store_rejects_invalid_json(tmp_path) -> None:
    path = tmp_path / "history.json"
    path.write_text("{invalid", encoding="utf-8")
    store = JsonGroupRunHistoryStore(path=path)

    with pytest.raises(GroupRunHistoryStoreError, match="invalid"):
        store.load()


def test_json_group_run_history_store_rejects_non_object_json(tmp_path) -> None:
    path = tmp_path / "history.json"
    path.write_text("[]", encoding="utf-8")
    store = JsonGroupRunHistoryStore(path=path)

    with pytest.raises(GroupRunHistoryStoreError, match="object"):
        store.load()


def test_json_group_run_history_store_rejects_invalid_datetime(tmp_path) -> None:
    path = tmp_path / "history.json"
    path.write_text('{"maquiagem-vip": "ontem"}', encoding="utf-8")
    store = JsonGroupRunHistoryStore(path=path)

    with pytest.raises(GroupRunHistoryStoreError, match="datetime"):
        store.load()
