import json

import pytest

from ofertas_bot.storage.json_group_plan_store import (
    GroupPlanStoreError,
    JsonGroupPlanStore,
)


def test_json_group_plan_store_saves_and_loads_summary(tmp_path) -> None:
    path = tmp_path / "plans" / "summary.json"
    summary = {
        "total_groups": 2,
        "allowed_groups": 1,
        "blocked_groups": 1,
        "total_selected_offers": 2,
        "groups": [
            {
                "group_slug": "maquiagem-vip",
                "allowed": True,
                "selected_offer_count": 2,
                "reasons": [],
                "next_available_at": None,
            }
        ],
    }

    store = JsonGroupPlanStore(path=path)
    store.save(summary)

    assert store.load() == summary


def test_json_group_plan_store_returns_empty_when_missing(tmp_path) -> None:
    store = JsonGroupPlanStore(path=tmp_path / "missing.json")

    assert store.load() == {}


def test_json_group_plan_store_rejects_invalid_json(tmp_path) -> None:
    path = tmp_path / "summary.json"
    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(GroupPlanStoreError, match="invalid"):
        JsonGroupPlanStore(path=path).load()


def test_json_group_plan_store_rejects_non_object_payload(tmp_path) -> None:
    path = tmp_path / "summary.json"
    path.write_text(json.dumps([]), encoding="utf-8")

    with pytest.raises(GroupPlanStoreError, match="object"):
        JsonGroupPlanStore(path=path).load()
