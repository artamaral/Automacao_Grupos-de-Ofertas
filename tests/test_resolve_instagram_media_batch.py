from __future__ import annotations

from datetime import date
from typing import Any

from ofertas_bot.storage.supabase_offer_media_asset_store import (
    InstagramMediaDispatchCandidate,
    OfferMediaAssetUpsert,
)
from ofertas_bot.tools import resolve_instagram_media_batch as batch


class FakeStore:
    def __init__(self) -> None:
        self.upserts: list[OfferMediaAssetUpsert] = []
        self.closed = False
        self.load_args: dict[str, Any] | None = None

    def load_dispatch_candidates(self, **kwargs: Any) -> list[InstagramMediaDispatchCandidate]:
        self.load_args = kwargs
        return [
            InstagramMediaDispatchCandidate(
                dispatch_plan_id="plan-1",
                profile="feminino",
                marketplace="shopee",
                stable_key="a" * 64,
                item_id=20,
                shop_id=10,
                product_link="https://shopee.com.br/product/10/20",
                planned_date=date(2026, 8, 15),
                planned_hour=10,
                slot_sequence=1,
                daily_sequence=1,
                primary_subniche="maquiagem-geral",
            )
        ]

    def upsert_media_asset(self, upsert: OfferMediaAssetUpsert) -> str:
        self.upserts.append(upsert)
        return "media-1"

    def close(self) -> None:
        self.closed = True


class FakeResponse:
    def __init__(self, body: bytes, *, headers: dict[str, str] | None = None) -> None:
        self._body = body
        self.status = 200
        self.headers = headers or {}

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self, *_: object) -> bytes:
        return self._body


def test_batch_dry_run_loads_candidates_without_writing(capsys) -> None:
    store = FakeStore()
    image_url = "https://cf.shopee.com.br/file/br-11134207-820m6-primary"
    video_url = "https://mms.vod.susercontent.com/api/v4/11110105/mms/item.mp4"

    def opener(request: Any, *, timeout: float) -> FakeResponse:
        del timeout
        if request.full_url == "https://shopee.com.br/product/10/20":
            return FakeResponse(
                b'{"images":["br-11134207-820m6-primary"],'
                b'"video":"https://mms.vod.susercontent.com/api/v4/11110105/mms/item.mp4"}',
            )
        headers = {
            image_url: {"Content-Type": "image/jpeg"},
            video_url: {"Content-Type": "video/mp4"},
        }
        return FakeResponse(b"x", headers=headers[request.full_url])

    exit_code = batch.run(
        [
            "--profile",
            "feminino",
            "--marketplace",
            "shopee",
            "--date",
            "2026-08-15",
            "--limit",
            "1",
            "--dry-run",
            "--only-missing",
            "--subniche",
            "maquiagem-geral",
        ],
        store_factory=lambda: store,
        opener=opener,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert store.upserts == []
    assert store.closed is True
    assert store.load_args == {
        "profile": "feminino",
        "marketplace": "shopee",
        "planned_date": date(2026, 8, 15),
        "limit": 1,
        "only_missing": True,
        "subniche": "maquiagem-geral",
    }
    assert "dry_run=true" in output
    assert "processed=1" in output
    assert "valid=1" in output
    assert "with_video=1" in output


def test_batch_apply_writes_upserts() -> None:
    store = FakeStore()

    def opener(request: Any, *, timeout: float) -> FakeResponse:
        del timeout
        if request.full_url == "https://shopee.com.br/product/10/20":
            return FakeResponse(b'{"images":["br-11134207-820m6-primary"]}')
        return FakeResponse(b"x", headers={"Content-Type": "image/jpeg"})

    batch.run(
        [
            "--profile",
            "feminino",
            "--marketplace",
            "shopee",
            "--date",
            "2026-08-15",
            "--limit",
            "1",
            "--apply",
        ],
        store_factory=lambda: store,
        opener=opener,
    )

    assert len(store.upserts) == 1
    assert store.upserts[0].status == "valid"
    assert store.upserts[0].image_urls == ("https://cf.shopee.com.br/file/br-11134207-820m6-primary",)
