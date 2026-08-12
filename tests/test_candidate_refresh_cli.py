from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from ofertas_bot.candidate_refresh import DiscoveryCandidate, SnapshotInput
from ofertas_bot.tools.candidate_refresh import run_candidate_refresh

NOW = datetime(2026, 8, 11, 12, tzinfo=UTC)


class FakeProvider:
    def __init__(self, responses: dict[int, dict[str, object]]) -> None:
        self.responses = responses
        self.calls: list[int] = []

    def fetch_product_offer_raw_response(
        self,
        *,
        limit: int,
        page: int = 1,
        item_id: int | None = None,
        **kwargs: object,
    ) -> dict[str, object]:
        assert limit == 1
        assert page == 1
        assert item_id is not None
        self.calls.append(item_id)
        return self.responses[item_id]


class FakeStore:
    def __init__(self, candidates: list[DiscoveryCandidate]) -> None:
        self.candidates = {item.item_id: item for item in candidates}
        self.snapshots: list[SnapshotInput] = []
        self.failures: list[dict[str, object]] = []

    def load_ttl_hours(self, *, profile: str, marketplace: str) -> int:
        return 24

    def load_discovery_candidates(
        self,
        *,
        profile: str,
        marketplace: str,
        item_ids: list[int] | None = None,
    ) -> list[DiscoveryCandidate]:
        if item_ids is not None:
            return [self.candidates[item_id] for item_id in item_ids]
        return list(self.candidates.values())

    def load_scoring_candidates(
        self,
        *,
        profile: str,
        marketplace: str,
        item_ids: list[int],
    ) -> list[object]:
        return []

    def record_success(self, *, profile: str, snapshot: SnapshotInput) -> int:
        self.snapshots.append(snapshot)
        candidate = self.candidates[snapshot.item_id]
        self.candidates[snapshot.item_id] = replace(
            candidate,
            refresh_status="FRESH",
            last_checked_at=snapshot.checked_at,
            last_attempted_at=snapshot.checked_at,
            last_attempt_status="success",
        )
        return len(self.snapshots)

    def record_failure(self, **values: object) -> None:
        self.failures.append(values)
        item_id = int(values["item_id"])
        candidate = self.candidates[item_id]
        self.candidates[item_id] = replace(
            candidate,
            last_attempted_at=values["attempted_at"],
            last_attempt_status=str(values["status"]),
        )


def test_apply_limit_preserves_success_and_defers_remaining_candidates(tmp_path: Path) -> None:
    store = FakeStore([_candidate(1), _candidate(2), _candidate(3)])
    provider = FakeProvider({item_id: _response(item_id) for item_id in range(1, 4)})

    result = _run(tmp_path, store=store, provider=provider, discovery_limit=3, max_calls=1)

    assert provider.calls == [1]
    assert [snapshot.item_id for snapshot in store.snapshots] == [1]
    assert result.report["summary"]["deferred_refreshes"] == 2
    assert result.report["run_status"] == "partial"


def test_next_run_advances_to_next_missing_item(tmp_path: Path) -> None:
    store = FakeStore([_candidate(1), _candidate(2)])
    provider = FakeProvider({1: _response(1), 2: _response(2)})
    _run(tmp_path, store=store, provider=provider, discovery_limit=1, run_id="first")

    second = _run(
        tmp_path,
        store=store,
        provider=provider,
        discovery_limit=1,
        run_id="second",
    )

    assert provider.calls == [1, 2]
    assert second.report["summary"]["successful_refreshes"] == 1


def test_explicit_fresh_item_is_cache_hit_without_snapshot(tmp_path: Path) -> None:
    fresh = replace(
        _candidate(1),
        refresh_status="FRESH",
        last_checked_at=NOW,
        last_attempted_at=NOW,
        last_attempt_status="success",
    )
    store = FakeStore([fresh])
    provider = FakeProvider({1: _response(1)})

    result = _run(tmp_path, store=store, provider=provider, item_ids=[1])

    assert provider.calls == []
    assert store.snapshots == []
    assert result.report["summary"]["fresh_cache_hits"] == 1
    assert result.report["summary"]["api_calls_attempted"] == 0


def test_no_node_records_attempt_without_snapshot(tmp_path: Path) -> None:
    store = FakeStore([_candidate(1)])
    provider = FakeProvider(
        {1: {"data": {"productOfferV2": {"nodes": [], "pageInfo": {"page": 1}}}}}
    )

    result = _run(tmp_path, store=store, provider=provider)

    assert store.snapshots == []
    assert store.failures[0]["status"] == "no_node"
    assert result.report["summary"]["no_node_refreshes"] == 1


def test_confirmed_unavailable_items_leave_the_automatic_queue(tmp_path: Path) -> None:
    store = FakeStore(
        [
            _candidate(1, refresh_status="UNAVAILABLE_CONFIRMED"),
            _candidate(2),
        ]
    )
    provider = FakeProvider({2: _response(2)})

    _run(tmp_path, store=store, provider=provider, discovery_limit=2)

    assert provider.calls == [2]


def test_explicit_item_can_recheck_confirmed_unavailable_candidate(tmp_path: Path) -> None:
    store = FakeStore([_candidate(1, refresh_status="UNAVAILABLE_CONFIRMED")])
    provider = FakeProvider({1: _response(1)})

    result = _run(tmp_path, store=store, provider=provider, item_ids=[1])

    assert provider.calls == [1]
    assert result.report["summary"]["successful_refreshes"] == 1


def test_two_real_verifications_preserve_two_snapshots(tmp_path: Path) -> None:
    store = FakeStore([_candidate(1)])
    provider = FakeProvider({1: _response(1, price="100")})
    _run(tmp_path, store=store, provider=provider, item_ids=[1], run_id="price-100")
    store.candidates[1] = replace(store.candidates[1], refresh_status="STALE")
    provider.responses[1] = _response(1, price="90")

    _run(tmp_path, store=store, provider=provider, item_ids=[1], run_id="price-90")

    assert [snapshot.price for snapshot in store.snapshots] == [100, 90]


def _run(
    tmp_path: Path,
    *,
    store: FakeStore,
    provider: FakeProvider,
    discovery_limit: int = 1,
    max_calls: int = 10,
    item_ids: list[int] | None = None,
    run_id: str = "run",
):
    return run_candidate_refresh(
        profile="feminino",
        marketplace="shopee",
        discovery_limit=discovery_limit,
        scoring_limit=1,
        max_api_calls=max_calls,
        item_ids=item_ids,
        output_base_dir=tmp_path,
        run_id=run_id,
        apply=True,
        store=store,
        provider=provider,
    )


def _candidate(item_id: int, *, refresh_status: str = "MISSING") -> DiscoveryCandidate:
    return DiscoveryCandidate(
        catalog_item_id=item_id,
        profile="feminino",
        marketplace="shopee",
        stable_key=f"key-{item_id}",
        item_id=item_id,
        product_name=f"Produto {item_id}",
        product_link=f"https://shopee.com.br/product/{item_id}/{item_id}",
        image_url=None,
        subniches=("maquiagem-olhos",),
        primary_subniche="maquiagem-olhos",
        refresh_status=refresh_status,
        last_checked_at=None,
        last_attempted_at=None,
        last_attempt_status=None,
        seller_key=f"shop:{item_id}",
        rank_profile=item_id,
        rank_subniche=item_id,
        commercial_score=100 - item_id,
    )


def _response(item_id: int, *, price: str = "90") -> dict[str, object]:
    return {
        "data": {
            "productOfferV2": {
                "nodes": [
                    {
                        "itemId": item_id,
                        "productName": f"Produto {item_id}",
                        "productLink": f"https://shopee.com.br/product/{item_id}/{item_id}",
                        "offerLink": f"https://s.shopee.com.br/{item_id}",
                        "price": price,
                        "priceMax": "100",
                        "sales": 100,
                        "ratingStar": "4.9",
                    }
                ],
                "pageInfo": {"page": 1, "limit": 1, "hasNextPage": False},
            }
        }
    }
