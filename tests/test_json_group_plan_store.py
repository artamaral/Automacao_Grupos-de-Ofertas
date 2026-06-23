import json
from datetime import UTC, datetime

import pytest

from ofertas_bot.group_plan import GroupPlanBuilder
from ofertas_bot.group_profiles import GroupProfile
from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.storage.json_group_plan_store import (
    GroupPlanStoreError,
    JsonGroupPlanStore,
)


def make_offer() -> Offer:
    return Offer(
        marketplace=Marketplace.MOCK,
        title="Oferta",
        url="https://example.test/oferta",
        image_url=None,
        price=49.9,
        old_price=None,
        commission_rate=0.05,
        sales_count=10,
        rating=4.5,
        niche="maquiagem",
        is_prime_or_free_shipping=True,
    )


def make_profile() -> GroupProfile:
    return GroupProfile(
        slug="maquiagem-vip",
        name="Maquiagem VIP",
        allowed_niches=("maquiagem",),
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


def test_json_group_plan_store_saves_group_plans(tmp_path) -> None:
    path = tmp_path / "plans" / "summary.json"
    plans = GroupPlanBuilder().build_plans(
        group_profiles=(make_profile(),),
        offers=[make_offer()],
        now=datetime(2026, 6, 23, 18, 0, tzinfo=UTC),
    )

    store = JsonGroupPlanStore(path=path)
    store.save_plans(plans)

    summary = store.load()
    assert summary["total_groups"] == 1
    assert summary["allowed_groups"] == 1
    assert summary["total_selected_offers"] == 1
    assert summary["groups"][0]["group_slug"] == "maquiagem-vip"


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
