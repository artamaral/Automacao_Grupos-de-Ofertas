from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.request import urlopen

from ofertas_bot.storage.supabase_offer_media_asset_store import (
    InstagramMediaDispatchCandidate,
    OfferMediaAssetUpsert,
    SupabaseOfferMediaAssetStore,
    build_offer_media_asset_upsert,
)
from ofertas_bot.tools.scrape_shopee_media import (
    DEFAULT_TIMEOUT_SECONDS,
    ShopeeMediaScrapeError,
    resolve_shopee_media,
)


@dataclass(frozen=True)
class BatchSummary:
    processed: int = 0
    valid: int = 0
    with_video: int = 0
    image_only: int = 0
    no_media: int = 0
    failed: int = 0
    total_images: int = 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve midias Instagram para itens planejados no Supabase."
    )
    parser.add_argument("--profile", required=True)
    parser.add_argument("--marketplace", default="shopee")
    parser.add_argument("--date", required=True, dest="planned_date")
    parser.add_argument("--limit", type=int, default=20)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True)
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--only-missing", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--subniche")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    return parser


def run(
    argv: Sequence[str] | None = None,
    *,
    store_factory: Callable[[], SupabaseOfferMediaAssetStore] | None = None,
    opener: Callable[..., object] = urlopen,
) -> int:
    args = build_parser().parse_args(argv)
    dry_run = not args.apply
    store = (store_factory or SupabaseOfferMediaAssetStore.connect_from_env)()
    try:
        candidates = store.load_dispatch_candidates(
            profile=args.profile,
            marketplace=args.marketplace,
            planned_date=date.fromisoformat(args.planned_date),
            limit=args.limit,
            only_missing=args.only_missing,
            subniche=args.subniche,
        )
        upserts = resolve_candidates(
            candidates,
            timeout_seconds=args.timeout,
            opener=opener,
        )
        if not dry_run:
            for upsert in upserts:
                store.upsert_media_asset(upsert)
        if args.output:
            write_debug_csv(args.output, upserts)
        print_summary(summarize(upserts), dry_run=dry_run)
    finally:
        store.close()
    return 0


def resolve_candidates(
    candidates: list[InstagramMediaDispatchCandidate],
    *,
    timeout_seconds: float,
    opener: Callable[..., object],
) -> list[OfferMediaAssetUpsert]:
    upserts: list[OfferMediaAssetUpsert] = []
    for candidate in candidates:
        try:
            result = resolve_shopee_media(
                source_url=candidate.product_link,
                item_id=str(candidate.item_id),
                shop_id=str(candidate.shop_id) if candidate.shop_id is not None else None,
                timeout_seconds=timeout_seconds,
                validate=True,
                opener=opener,
            )
            upserts.append(
                build_offer_media_asset_upsert(
                    profile=candidate.profile,
                    marketplace=candidate.marketplace,
                    product_link=candidate.product_link,
                    scrape_result=result,
                    item_id=candidate.item_id,
                    shop_id=candidate.shop_id,
                )
            )
        except ShopeeMediaScrapeError as error:
            upserts.append(
                build_offer_media_asset_upsert(
                    profile=candidate.profile,
                    marketplace=candidate.marketplace,
                    product_link=candidate.product_link,
                    scrape_result=None,
                    error_detail=str(error),
                    item_id=candidate.item_id,
                    shop_id=candidate.shop_id,
                )
            )
    return upserts


def summarize(upserts: list[OfferMediaAssetUpsert]) -> BatchSummary:
    return BatchSummary(
        processed=len(upserts),
        valid=sum(upsert.status == "valid" for upsert in upserts),
        with_video=sum(
            upsert.status == "valid" and upsert.video_url is not None
            for upsert in upserts
        ),
        image_only=sum(
            upsert.status == "valid" and upsert.video_url is None and bool(upsert.image_urls)
            for upsert in upserts
        ),
        no_media=sum(upsert.status == "no_media" for upsert in upserts),
        failed=sum(upsert.status == "failed" for upsert in upserts),
        total_images=sum(len(upsert.image_urls) for upsert in upserts),
    )


def print_summary(summary: BatchSummary, *, dry_run: bool) -> None:
    print(f"dry_run={str(dry_run).lower()}")
    print(f"processed={summary.processed}")
    print(f"valid={summary.valid}")
    print(f"with_video={summary.with_video}")
    print(f"image_only={summary.image_only}")
    print(f"no_media={summary.no_media}")
    print(f"failed={summary.failed}")
    print(f"total_images={summary.total_images}")


def write_debug_csv(output_path: Path, upserts: list[OfferMediaAssetUpsert]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "profile",
                "marketplace",
                "item_id",
                "shop_id",
                "product_link",
                "status",
                "image_count",
                "video_url",
                "error_detail",
            ],
        )
        writer.writeheader()
        for upsert in upserts:
            writer.writerow(
                {
                    "profile": upsert.profile,
                    "marketplace": upsert.marketplace,
                    "item_id": upsert.item_id,
                    "shop_id": upsert.shop_id or "",
                    "product_link": upsert.product_link,
                    "status": upsert.status,
                    "image_count": len(upsert.image_urls),
                    "video_url": upsert.video_url or "",
                    "error_detail": upsert.error_detail or "",
                }
            )


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(f"ERRO | {error}", file=sys.stderr)
        raise SystemExit(2) from error
