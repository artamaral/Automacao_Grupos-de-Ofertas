from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol

from ofertas_bot.agents.scorer import ScorerAgent
from ofertas_bot.candidate_refresh import (
    CandidateRefreshError,
    DiscoveryCandidate,
    ScoringCandidate,
    SnapshotInput,
    select_progressive_candidates,
    select_scoring_candidates,
    snapshot_from_product_offer_response,
)
from ofertas_bot.models import ScoredOffer
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.selection import apply_default_selection_policy, resolve_selection_policy
from ofertas_bot.settings import get_settings
from ofertas_bot.storage.supabase_candidate_refresh_store import (
    SupabaseCandidateRefreshStore,
)

CONFIRMATION = "REFRESH_SHOPEE_CANDIDATES"
DEFAULT_OUTPUT_BASE_DIR = Path(".data/candidate_refresh")
DISCOVERY_FIELDNAMES = (
    "item_id",
    "product_name",
    "primary_subniche",
    "refresh_status",
    "last_checked_at",
    "last_attempted_at",
    "last_attempt_status",
    "seller_key",
)
ATTEMPT_FIELDNAMES = (
    "item_id",
    "refresh_status_before",
    "status",
    "attempted_at",
    "snapshot_id",
    "detail",
)
SCORING_FIELDNAMES = (
    "item_id",
    "product_name",
    "primary_subniche",
    "price",
    "reference_price",
    "commission_rate",
    "sales_count",
    "rating",
    "shop_type_code",
    "last_checked_at",
    "offer_link",
)
SCORED_FIELDNAMES = (
    "item_id",
    "product_name",
    "price",
    "reference_price",
    "commission_rate",
    "sales_count",
    "rating",
    "score",
    "score_reasons",
    "offer_link",
)


class ProductOfferProvider(Protocol):
    def fetch_product_offer_raw_response(
        self,
        *,
        limit: int,
        page: int = 1,
        item_id: int | None = None,
        **kwargs: object,
    ) -> dict[str, Any]:
        ...


class CandidateRefreshStore(Protocol):
    def load_ttl_hours(self, *, profile: str, marketplace: str) -> int:
        ...

    def load_discovery_candidates(
        self,
        *,
        profile: str,
        marketplace: str,
        item_ids: Sequence[int] | None = None,
    ) -> list[DiscoveryCandidate]:
        ...

    def load_scoring_candidates(
        self,
        *,
        profile: str,
        marketplace: str,
        item_ids: Sequence[int],
    ) -> list[ScoringCandidate]:
        ...

    def record_success(self, *, profile: str, snapshot: SnapshotInput) -> int:
        ...

    def record_failure(
        self,
        *,
        profile: str,
        marketplace: str,
        item_id: int,
        attempted_at: datetime,
        status: str,
        error_type: str,
        error_detail: str,
    ) -> None:
        ...


@dataclass(frozen=True)
class CandidateRefreshPaths:
    output_dir: Path
    discovery_candidates: Path
    refresh_attempts: Path
    scoring_candidates: Path
    scored_candidates: Path
    selected_offers: Path
    run_report: Path


@dataclass(frozen=True)
class CandidateRefreshRunResult:
    paths: CandidateRefreshPaths
    report: dict[str, Any]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa fila progressiva de refresh comercial da Shopee."
    )
    parser.add_argument("--profile", required=True)
    parser.add_argument("--marketplace", default="shopee")
    parser.add_argument("--discovery-limit", type=int, default=600)
    parser.add_argument("--scoring-limit", type=int, default=200)
    parser.add_argument("--max-api-calls", type=int, default=100)
    parser.add_argument("--item-id", type=int, action="append", default=None)
    parser.add_argument("--output-base-dir", type=Path, default=DEFAULT_OUTPUT_BASE_DIR)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-remote-write")
    return parser


def run(
    argv: Sequence[str] | None = None,
    *,
    store: CandidateRefreshStore | None = None,
    provider: ProductOfferProvider | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    owned_store: SupabaseCandidateRefreshStore | None = None
    try:
        _validate_args(args)
        if store is None:
            owned_store = SupabaseCandidateRefreshStore.connect_from_env()
            store = owned_store
        if args.apply and provider is None:
            shopee_provider = ShopeeProvider(settings=get_settings())
            shopee_provider.validate_real_http_ready()
            provider = shopee_provider
        result = run_candidate_refresh(
            profile=args.profile,
            marketplace=args.marketplace,
            discovery_limit=args.discovery_limit,
            scoring_limit=args.scoring_limit,
            max_api_calls=args.max_api_calls,
            item_ids=args.item_id,
            output_base_dir=args.output_base_dir,
            run_id=args.run_id,
            apply=args.apply,
            store=store,
            provider=provider,
        )
    except Exception as error:  # noqa: BLE001 - CLI reports provider/database failures.
        print("ERRO | Refresh progressivo bloqueado", file=sys.stderr)
        print(f"DETALHE | {error}", file=sys.stderr)
        return 3
    finally:
        if owned_store is not None:
            owned_store.close()

    _print_summary(result.report)
    return 0


def run_candidate_refresh(
    *,
    profile: str,
    marketplace: str,
    discovery_limit: int,
    scoring_limit: int,
    max_api_calls: int,
    item_ids: Sequence[int] | None,
    output_base_dir: Path,
    run_id: str | None,
    apply: bool,
    store: CandidateRefreshStore,
    provider: ProductOfferProvider | None,
) -> CandidateRefreshRunResult:
    started = perf_counter()
    resolved_run_id = run_id or datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S-%fZ")
    paths = _build_paths(output_base_dir, profile, resolved_run_id)
    paths.output_dir.mkdir(parents=True, exist_ok=True)

    ttl_hours = store.load_ttl_hours(profile=profile, marketplace=marketplace)
    policy = resolve_selection_policy(profile)
    if policy is None:
        raise CandidateRefreshError(f"selection policy not found: {profile}")

    all_candidates = store.load_discovery_candidates(
        profile=profile,
        marketplace=marketplace,
        item_ids=item_ids,
    )
    if item_ids is not None:
        discovery_candidates = all_candidates
    else:
        discovery_candidates = select_progressive_candidates(
            all_candidates,
            limit=discovery_limit,
            subniche_weights=policy.subniche_quotas,
        )

    attempt_rows: list[dict[str, Any]] = []
    api_calls = 0
    successful_refreshes = 0
    failed_refreshes = 0
    no_node_refreshes = 0
    deferred_refreshes = 0
    cache_hits = 0
    snapshots_inserted = 0

    for candidate in discovery_candidates:
        if candidate.refresh_status == "FRESH":
            cache_hits += 1
            attempt_rows.append(_attempt_row(candidate, status="cache_hit"))
            continue
        if not apply:
            attempt_rows.append(_attempt_row(candidate, status="planned_api_call"))
            continue
        if api_calls >= max_api_calls:
            deferred_refreshes += 1
            attempt_rows.append(_attempt_row(candidate, status="deferred_api_limit"))
            continue
        if provider is None:
            raise CandidateRefreshError("provider is required for --apply")

        attempted_at = datetime.now(UTC)
        api_calls += 1
        try:
            response = provider.fetch_product_offer_raw_response(
                limit=1,
                page=1,
                item_id=candidate.item_id,
            )
        except Exception as error:  # noqa: BLE001 - every real attempt is audited.
            store.record_failure(
                profile=profile,
                marketplace=marketplace,
                item_id=candidate.item_id,
                attempted_at=attempted_at,
                status="technical_failure",
                error_type=type(error).__name__,
                error_detail=str(error),
            )
            failed_refreshes += 1
            attempt_rows.append(
                _attempt_row(
                    candidate,
                    status="technical_failure",
                    attempted_at=attempted_at,
                    detail=f"{type(error).__name__}: {error}",
                )
            )
            continue

        try:
            snapshot = snapshot_from_product_offer_response(
                response=response,
                requested_item_id=candidate.item_id,
                checked_at=attempted_at,
            )
        except CandidateRefreshError as error:
            store.record_failure(
                profile=profile,
                marketplace=marketplace,
                item_id=candidate.item_id,
                attempted_at=attempted_at,
                status="invalid_payload",
                error_type=type(error).__name__,
                error_detail=str(error),
            )
            failed_refreshes += 1
            attempt_rows.append(
                _attempt_row(
                    candidate,
                    status="invalid_payload",
                    attempted_at=attempted_at,
                    detail=str(error),
                )
            )
            continue

        if snapshot is None:
            store.record_failure(
                profile=profile,
                marketplace=marketplace,
                item_id=candidate.item_id,
                attempted_at=attempted_at,
                status="no_node",
                error_type="NoNode",
                error_detail="productOfferV2 returned no nodes",
            )
            no_node_refreshes += 1
            attempt_rows.append(
                _attempt_row(
                    candidate,
                    status="no_node",
                    attempted_at=attempted_at,
                    detail="productOfferV2 returned no nodes",
                )
            )
            continue

        snapshot_id = store.record_success(profile=profile, snapshot=snapshot)
        successful_refreshes += 1
        snapshots_inserted += 1
        attempt_rows.append(
            _attempt_row(
                candidate,
                status="success",
                attempted_at=attempted_at,
                snapshot_id=snapshot_id,
            )
        )

    discovery_item_ids = [candidate.item_id for candidate in discovery_candidates]
    fresh_valid_candidates = store.load_scoring_candidates(
        profile=profile,
        marketplace=marketplace,
        item_ids=discovery_item_ids,
    )
    scoring_candidates = select_scoring_candidates(
        fresh_valid_candidates,
        limit=scoring_limit,
        subniche_weights=policy.subniche_quotas,
    )
    offers = [candidate.to_offer() for candidate in scoring_candidates]
    scored = ScorerAgent().score(offers)
    subniche_by_url = {
        candidate.offer_link: candidate.primary_subniche for candidate in scoring_candidates
    }
    selection = apply_default_selection_policy(
        scored,
        niche=profile,
        catalog_source_path=None,
        subniche_by_url=subniche_by_url,
    )

    _write_csv(
        paths.discovery_candidates,
        [_discovery_row(item) for item in discovery_candidates],
        fieldnames=DISCOVERY_FIELDNAMES,
    )
    _write_csv(paths.refresh_attempts, attempt_rows, fieldnames=ATTEMPT_FIELDNAMES)
    _write_csv(
        paths.scoring_candidates,
        [_scoring_row(item) for item in scoring_candidates],
        fieldnames=SCORING_FIELDNAMES,
    )
    _write_csv(
        paths.scored_candidates,
        [_scored_row(item) for item in scored],
        fieldnames=SCORED_FIELDNAMES,
    )
    _write_csv(
        paths.selected_offers,
        [_scored_row(item) for item in selection.scored_offers],
        fieldnames=SCORED_FIELDNAMES,
    )

    status_counts = Counter(item.refresh_status for item in discovery_candidates)
    never_attempted = sum(
        item.refresh_status == "MISSING" and item.last_attempted_at is None
        for item in discovery_candidates
    )
    run_status = "partial" if deferred_refreshes else "completed"
    if failed_refreshes or no_node_refreshes:
        run_status = f"{run_status}_with_failures"
    report = {
        "profile": profile,
        "marketplace": marketplace,
        "run_id": resolved_run_id,
        "mode": "apply" if apply else "dry_run",
        "run_status": run_status,
        "ttl_hours": ttl_hours,
        "limits": {
            "discovery": discovery_limit,
            "scoring": scoring_limit,
            "max_api_calls": max_api_calls,
        },
        "summary": {
            "catalog_candidates_available": len(all_candidates),
            "discovery_candidates": len(discovery_candidates),
            "missing_candidates": status_counts["MISSING"],
            "missing_never_attempted": never_attempted,
            "stale_candidates": status_counts["STALE"],
            "fresh_candidates": status_counts["FRESH"],
            "fresh_cache_hits": cache_hits,
            "planned_api_calls": sum(
                row["status"] == "planned_api_call" for row in attempt_rows
            ),
            "api_calls_attempted": api_calls,
            "successful_refreshes": successful_refreshes,
            "failed_refreshes": failed_refreshes,
            "no_node_refreshes": no_node_refreshes,
            "deferred_refreshes": deferred_refreshes,
            "snapshots_inserted": snapshots_inserted,
            "fresh_valid_candidates": len(fresh_valid_candidates),
            "candidates_sent_to_scorer": len(scoring_candidates),
            "selected_by_gate": len(selection.scored_offers),
            "cache_calls_saved": cache_hits,
            "elapsed_seconds": round(perf_counter() - started, 3),
        },
        "outputs": {key: value.as_posix() for key, value in asdict(paths).items()},
    }
    paths.run_report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return CandidateRefreshRunResult(paths=paths, report=report)


def _validate_args(args: argparse.Namespace) -> None:
    if args.profile != "feminino":
        raise CandidateRefreshError("this version only supports --profile feminino")
    if args.marketplace != "shopee":
        raise CandidateRefreshError("this version only supports --marketplace shopee")
    if args.discovery_limit <= 0 or args.scoring_limit <= 0:
        raise CandidateRefreshError("discovery and scoring limits must be positive")
    if args.max_api_calls <= 0:
        raise CandidateRefreshError("--max-api-calls must be positive")
    if args.apply and args.dry_run:
        raise CandidateRefreshError("--apply and --dry-run are mutually exclusive")
    if args.apply and args.confirm_remote_write != CONFIRMATION:
        raise CandidateRefreshError(
            f"--confirm-remote-write must be exactly {CONFIRMATION}"
        )
    if not args.apply and args.confirm_remote_write:
        raise CandidateRefreshError("--confirm-remote-write requires --apply")
    if args.item_id and any(item_id <= 0 for item_id in args.item_id):
        raise CandidateRefreshError("--item-id must be positive")
    if args.item_id and len(set(args.item_id)) != len(args.item_id):
        raise CandidateRefreshError("--item-id values must be unique")


def _build_paths(base_dir: Path, profile: str, run_id: str) -> CandidateRefreshPaths:
    output_dir = base_dir / profile / run_id
    return CandidateRefreshPaths(
        output_dir=output_dir,
        discovery_candidates=output_dir / "discovery_candidates.csv",
        refresh_attempts=output_dir / "refresh_attempts.csv",
        scoring_candidates=output_dir / "scoring_candidates.csv",
        scored_candidates=output_dir / "scored_candidates.csv",
        selected_offers=output_dir / "selected_offers.csv",
        run_report=output_dir / "run_report.json",
    )


def _attempt_row(
    candidate: DiscoveryCandidate,
    *,
    status: str,
    attempted_at: datetime | None = None,
    snapshot_id: int | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    return {
        "item_id": candidate.item_id,
        "refresh_status_before": candidate.refresh_status,
        "status": status,
        "attempted_at": attempted_at.isoformat() if attempted_at else "",
        "snapshot_id": snapshot_id or "",
        "detail": detail or "",
    }


def _discovery_row(candidate: DiscoveryCandidate) -> dict[str, Any]:
    return {
        "item_id": candidate.item_id,
        "product_name": candidate.product_name,
        "primary_subniche": candidate.primary_subniche,
        "refresh_status": candidate.refresh_status,
        "last_checked_at": (
            candidate.last_checked_at.isoformat() if candidate.last_checked_at else ""
        ),
        "last_attempted_at": (
            candidate.last_attempted_at.isoformat() if candidate.last_attempted_at else ""
        ),
        "last_attempt_status": candidate.last_attempt_status or "",
        "seller_key": candidate.seller_key,
    }


def _scoring_row(candidate: ScoringCandidate) -> dict[str, Any]:
    return {
        "item_id": candidate.item_id,
        "product_name": candidate.product_name,
        "primary_subniche": candidate.primary_subniche,
        "price": candidate.price,
        "reference_price": candidate.reference_price or "",
        "commission_rate": candidate.commission_rate,
        "sales_count": candidate.sales_count,
        "rating": candidate.rating or "",
        "shop_type_code": candidate.shop_type_code or "",
        "last_checked_at": candidate.last_checked_at.isoformat(),
        "offer_link": candidate.offer_link,
    }


def _scored_row(scored: ScoredOffer) -> dict[str, Any]:
    offer = scored.offer
    return {
        "item_id": offer.item_id,
        "product_name": offer.title,
        "price": offer.price,
        "reference_price": offer.old_price or "",
        "commission_rate": offer.commission_rate,
        "sales_count": offer.sales_count,
        "rating": offer.rating or "",
        "score": scored.score,
        "score_reasons": json.dumps(scored.reasons, ensure_ascii=False),
        "offer_link": offer.url,
    }


def _write_csv(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    fieldnames: Sequence[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _print_summary(report: Mapping[str, Any]) -> None:
    summary = report["summary"]
    print(f"Profile: {report['profile']}")
    print(f"Mode: {report['mode']}")
    print(f"Run status: {report['run_status']}")
    print(f"Discovery candidates: {summary['discovery_candidates']}")
    print(f"Missing: {summary['missing_candidates']}")
    print(f"Stale: {summary['stale_candidates']}")
    print(f"Fresh cache hits: {summary['fresh_cache_hits']}")
    print(f"API calls attempted: {summary['api_calls_attempted']}")
    print(f"API calls successful: {summary['successful_refreshes']}")
    print(f"API failures: {summary['failed_refreshes'] + summary['no_node_refreshes']}")
    print(f"Snapshots inserted: {summary['snapshots_inserted']}")
    print(f"Fresh valid candidates: {summary['fresh_valid_candidates']}")
    print(f"Candidates sent to scorer: {summary['candidates_sent_to_scorer']}")
    print(f"Selected by SelectionGate: {summary['selected_by_gate']}")


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
