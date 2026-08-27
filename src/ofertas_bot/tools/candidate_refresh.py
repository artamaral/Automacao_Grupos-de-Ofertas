from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from ofertas_bot.agents.scorer import ScorerAgent
from ofertas_bot.candidate_refresh import (
    CandidateRefreshError,
    DiscoveryCandidate,
    ScoringCandidate,
    SnapshotInput,
    scale_subniche_quotas,
    select_ranked_refresh_candidates,
    select_scoring_candidates,
    snapshot_from_product_offer_response,
)
from ofertas_bot.distribution_strategy import resolve_profile_distribution_strategy
from ofertas_bot.models import ScoredOffer
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.selection import apply_default_selection_policy
from ofertas_bot.settings import get_settings
from ofertas_bot.storage.supabase_candidate_refresh_store import (
    SupabaseCandidateRefreshStore,
)

CONFIRMATION = "REFRESH_SHOPEE_CANDIDATES"
DEFAULT_OUTPUT_BASE_DIR = Path(".data/candidate_refresh")
OPERATIONAL_TZ = ZoneInfo("America/Sao_Paulo")
DISCOVERY_FIELDNAMES = (
    "item_id",
    "product_name",
    "primary_subniche",
    "refresh_status",
    "last_checked_at",
    "last_attempted_at",
    "last_attempt_status",
    "seller_key",
    "rank_profile",
    "rank_subniche",
    "commercial_score",
    "commercial_data_source",
    "selection_bucket",
)
ATTEMPT_FIELDNAMES = (
    "item_id",
    "primary_subniche",
    "selection_bucket",
    "rank_subniche",
    "refresh_status_before",
    "status",
    "attempted_at",
    "snapshot_id",
    "detail",
)
RANKING_CHANGE_FIELDNAMES = (
    "item_id",
    "primary_subniche",
    "rank_before",
    "rank_after",
    "score_before",
    "score_after",
    "source_before",
    "source_after",
    "refresh_before",
    "refresh_after",
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
        operational_date: date,
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
    ranking_changes: Path
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
    parser.add_argument("--discovery-limit", type=int, default=500)
    parser.add_argument("--scoring-limit", type=int, default=200)
    parser.add_argument("--max-api-calls", type=int, default=500)
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
    operational_date: date | None = None,
) -> CandidateRefreshRunResult:
    started = perf_counter()
    resolved_run_id = run_id or datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S-%fZ")
    resolved_operational_date = operational_date or datetime.now(OPERATIONAL_TZ).date()
    paths = _build_paths(output_base_dir, profile, resolved_run_id)
    paths.output_dir.mkdir(parents=True, exist_ok=True)

    ttl_hours = store.load_ttl_hours(profile=profile, marketplace=marketplace)
    strategy = resolve_profile_distribution_strategy(
        profile,
        marketplace=marketplace,
        operational_date=resolved_operational_date,
    )

    all_candidates = store.load_discovery_candidates(
        profile=profile,
        marketplace=marketplace,
        item_ids=item_ids,
    )
    operational_candidates = [
        _with_operational_refresh_status(
            candidate,
            operational_date=resolved_operational_date,
        )
        for candidate in all_candidates
    ]
    if item_ids is not None:
        discovery_candidates = [
            replace(candidate, selection_bucket="explicit_item")
            for candidate in operational_candidates
        ]
    else:
        discovery_candidates = select_ranked_refresh_candidates(
            operational_candidates,
            limit=discovery_limit,
            subniche_weights=strategy.refresh_weights,
        )
    before_by_item = {candidate.item_id: candidate for candidate in discovery_candidates}

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
    after_candidates = store.load_discovery_candidates(
        profile=profile,
        marketplace=marketplace,
        item_ids=discovery_item_ids,
    )
    ranking_change_rows = [
        _ranking_change_row(before_by_item[item.item_id], item)
        for item in after_candidates
    ]
    fresh_valid_candidates = store.load_scoring_candidates(
        profile=profile,
        marketplace=marketplace,
        item_ids=discovery_item_ids,
        operational_date=resolved_operational_date,
    )
    scoring_candidates = select_scoring_candidates(
        fresh_valid_candidates,
        limit=scoring_limit,
        subniche_weights=strategy.refresh_weights,
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
    _write_csv(
        paths.ranking_changes,
        ranking_change_rows,
        fieldnames=RANKING_CHANGE_FIELDNAMES,
    )

    technical_by_item = {candidate.item_id: candidate for candidate in all_candidates}
    technical_status_counts = Counter(
        technical_by_item[item.item_id].refresh_status
        for item in discovery_candidates
        if item.item_id in technical_by_item
    )
    status_counts = Counter(item.refresh_status for item in discovery_candidates)
    old_date_refresh_candidates = sum(
        technical_by_item[item.item_id].refresh_status == "FRESH"
        and technical_by_item[item.item_id].last_checked_at is not None
        and not _is_same_operational_date(
            technical_by_item[item.item_id].last_checked_at,
            resolved_operational_date,
        )
        for item in discovery_candidates
        if item.item_id in technical_by_item
    )
    never_attempted = sum(
        item.refresh_status == "MISSING" and item.last_attempted_at is None
        for item in discovery_candidates
    )
    call_candidates = [
        item for item in discovery_candidates if item.refresh_status != "FRESH"
    ]
    bucket_counts = Counter(item.selection_bucket for item in call_candidates)
    calls_by_subniche = Counter(item.primary_subniche for item in call_candidates)
    ranking_limit = discovery_limit * 80 // 100
    exploration_limit = discovery_limit - ranking_limit
    planned_ranking = scale_subniche_quotas(
        limit=ranking_limit,
        weights=strategy.refresh_weights,
    )
    planned_exploration = scale_subniche_quotas(
        limit=exploration_limit,
        weights=strategy.refresh_weights,
    )
    rank_changes = sum(
        row["rank_before"] != row["rank_after"] for row in ranking_change_rows
    )
    source_changes = sum(
        row["source_before"] != row["source_after"] for row in ranking_change_rows
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
        "operational_date": resolved_operational_date.isoformat(),
        "operational_timezone": "America/Sao_Paulo",
        "distribution_strategy": {
            "planning_mode": strategy.planning_mode,
            "refresh_weights": strategy.refresh_weights,
            "discovery_weights": strategy.discovery_weights,
            "required_daily_quotas": strategy.required_daily_quotas,
        },
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
            "fresh_candidates": technical_status_counts["FRESH"],
            "fresh_cache_hits": cache_hits,
            "same_day_cache_hits": cache_hits,
            "old_date_refresh_candidates": old_date_refresh_candidates,
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
            "scoring_ready_candidates": len(fresh_valid_candidates),
            "scoring_candidates_refreshed_today": len(fresh_valid_candidates),
            "candidates_sent_to_scorer": len(scoring_candidates),
            "selected_by_gate": len(selection.scored_offers),
            "cache_calls_saved": cache_hits,
            "ranking_bucket_candidates": bucket_counts["ranking"],
            "exploration_bucket_candidates": bucket_counts["exploration"],
            "quota_fallback_candidates": bucket_counts["quota_fallback"],
            "rank_changes": rank_changes,
            "commercial_source_changes": source_changes,
            "elapsed_seconds": round(perf_counter() - started, 3),
        },
        "allocation": {
            "planned": {
                "ranking": planned_ranking,
                "exploration": planned_exploration,
            },
            "actual_api_candidates_by_bucket": dict(sorted(bucket_counts.items())),
            "actual_api_candidates_by_subniche": dict(sorted(calls_by_subniche.items())),
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


def _with_operational_refresh_status(
    candidate: DiscoveryCandidate,
    *,
    operational_date: date,
) -> DiscoveryCandidate:
    if candidate.refresh_status != "FRESH":
        return candidate
    if _is_same_operational_date(candidate.last_checked_at, operational_date):
        return candidate
    return replace(candidate, refresh_status="STALE")


def _is_same_operational_date(
    timestamp: datetime | None,
    operational_date: date,
) -> bool:
    if timestamp is None:
        return False
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(OPERATIONAL_TZ).date() == operational_date


def _build_paths(base_dir: Path, profile: str, run_id: str) -> CandidateRefreshPaths:
    output_dir = base_dir / profile / run_id
    return CandidateRefreshPaths(
        output_dir=output_dir,
        discovery_candidates=output_dir / "discovery_candidates.csv",
        refresh_attempts=output_dir / "refresh_attempts.csv",
        scoring_candidates=output_dir / "scoring_candidates.csv",
        scored_candidates=output_dir / "scored_candidates.csv",
        selected_offers=output_dir / "selected_offers.csv",
        ranking_changes=output_dir / "ranking_changes.csv",
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
        "primary_subniche": candidate.primary_subniche,
        "selection_bucket": candidate.selection_bucket,
        "rank_subniche": candidate.rank_subniche or "",
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
        "rank_profile": candidate.rank_profile or "",
        "rank_subniche": candidate.rank_subniche or "",
        "commercial_score": candidate.commercial_score or "",
        "commercial_data_source": candidate.commercial_data_source,
        "selection_bucket": candidate.selection_bucket,
    }


def _ranking_change_row(
    before: DiscoveryCandidate,
    after: DiscoveryCandidate,
) -> dict[str, Any]:
    return {
        "item_id": before.item_id,
        "primary_subniche": before.primary_subniche,
        "rank_before": before.rank_profile or "",
        "rank_after": after.rank_profile or "",
        "score_before": before.commercial_score or "",
        "score_after": after.commercial_score or "",
        "source_before": before.commercial_data_source,
        "source_after": after.commercial_data_source,
        "refresh_before": before.refresh_status,
        "refresh_after": after.refresh_status,
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
        "last_checked_at": (
            candidate.last_checked_at.isoformat() if candidate.last_checked_at else ""
        ),
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
    print(f"Scoring-ready candidates: {summary['scoring_ready_candidates']}")
    print(f"Candidates sent to scorer: {summary['candidates_sent_to_scorer']}")
    print(f"Selected by SelectionGate: {summary['selected_by_gate']}")


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
