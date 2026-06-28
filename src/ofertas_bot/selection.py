from __future__ import annotations

import csv
import json
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ofertas_bot.models import ScoredOffer

DEFAULT_SELECTION_PROFILES_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "selection_profiles.toml"
)


class SelectionPolicyError(ValueError):
    """Raised when an operational selection policy is invalid."""


@dataclass(frozen=True)
class SelectionPolicy:
    slug: str
    niche: str
    total_items: int
    max_zero_sales_items: int
    minimum_daily_runs: int
    cooldown_hours_default: int
    evidence: str
    subniche_quotas: dict[str, int]


def load_selection_policies(path: Path) -> dict[str, SelectionPolicy]:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SelectionPolicyError(f"selection policy file not found: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise SelectionPolicyError(f"invalid selection policy file: {error}") from error

    raw_policies = raw.get("policies")
    if not isinstance(raw_policies, list) or not raw_policies:
        raise SelectionPolicyError("selection policy file must define [[policies]]")

    policies: dict[str, SelectionPolicy] = {}
    for raw_policy in raw_policies:
        policy = _build_selection_policy(raw_policy)
        if policy.niche in policies:
            raise SelectionPolicyError(f"duplicate selection policy niche: {policy.niche}")
        policies[policy.niche] = policy
    return policies


def _build_selection_policy(raw_policy: object) -> SelectionPolicy:
    if not isinstance(raw_policy, dict):
        raise SelectionPolicyError("each selection policy must be an object")

    slug = str(raw_policy.get("slug", "")).strip().lower()
    niche = str(raw_policy.get("niche", "")).strip().lower()
    total_items = int(raw_policy.get("total_items", 0))
    max_zero_sales_items = int(raw_policy.get("max_zero_sales_items", -1))
    minimum_daily_runs = int(raw_policy.get("minimum_daily_runs", 0))
    cooldown_hours_default = int(raw_policy.get("cooldown_hours_default", 0))
    evidence = str(raw_policy.get("evidence", "")).strip()
    raw_bands = raw_policy.get("bands")

    if not slug or not niche:
        raise SelectionPolicyError("selection policy slug and niche are required")
    if total_items <= 0 or minimum_daily_runs <= 0:
        raise SelectionPolicyError(f"selection policy counts must be positive: {slug}")
    if cooldown_hours_default <= 0:
        raise SelectionPolicyError(f"selection policy cooldown must be positive: {slug}")
    if max_zero_sales_items < 0 or max_zero_sales_items > total_items:
        raise SelectionPolicyError(f"invalid zero-sales limit for selection policy: {slug}")
    if not evidence:
        raise SelectionPolicyError(f"selection policy evidence is required: {slug}")
    if not isinstance(raw_bands, list) or not raw_bands:
        raise SelectionPolicyError(f"selection policy bands are required: {slug}")

    quotas: dict[str, int] = {}
    total_share = 0
    for raw_band in raw_bands:
        if not isinstance(raw_band, dict):
            raise SelectionPolicyError(f"selection policy band must be an object: {slug}")
        subniche = str(raw_band.get("subniche", "")).strip()
        items = int(raw_band.get("items", 0))
        share_percent = int(raw_band.get("share_percent", 0))
        if not subniche or items <= 0 or share_percent <= 0:
            raise SelectionPolicyError(f"invalid selection policy band: {slug}")
        if subniche in quotas:
            raise SelectionPolicyError(f"duplicate subniche in selection policy: {subniche}")
        if share_percent * total_items != items * 100:
            raise SelectionPolicyError(
                f"selection policy share does not match item count: {slug}/{subniche}"
            )
        quotas[subniche] = items
        total_share += share_percent

    if sum(quotas.values()) != total_items:
        raise SelectionPolicyError(f"selection policy item total must equal {total_items}: {slug}")
    if total_share != 100:
        raise SelectionPolicyError(f"selection policy shares must total 100: {slug}")

    return SelectionPolicy(
        slug=slug,
        niche=niche,
        total_items=total_items,
        max_zero_sales_items=max_zero_sales_items,
        minimum_daily_runs=minimum_daily_runs,
        cooldown_hours_default=cooldown_hours_default,
        evidence=evidence,
        subniche_quotas=quotas,
    )


DEFAULT_SELECTION_POLICIES_BY_NICHE = load_selection_policies(
    DEFAULT_SELECTION_PROFILES_PATH
)
DEFAULT_SUBNICHE_QUOTAS_BY_NICHE = {
    niche: policy.subniche_quotas
    for niche, policy in DEFAULT_SELECTION_POLICIES_BY_NICHE.items()
}
DEFAULT_MAX_ZERO_SALES_ITEMS_BY_NICHE = {
    niche: policy.max_zero_sales_items
    for niche, policy in DEFAULT_SELECTION_POLICIES_BY_NICHE.items()
}


@dataclass(frozen=True)
class SelectionResult:
    scored_offers: list[ScoredOffer]
    applied_default_policy: bool
    selected_count: int
    quota_count: int


def apply_default_selection_policy(
    scored_offers: list[ScoredOffer],
    *,
    niche: str,
    catalog_source_path: Path | None,
) -> SelectionResult:
    normalized_niche = niche.strip().lower()
    eligible_scored_offers = _filter_eligible_scored_offers(scored_offers)
    quotas = DEFAULT_SUBNICHE_QUOTAS_BY_NICHE.get(normalized_niche)
    max_zero_sales_items = DEFAULT_MAX_ZERO_SALES_ITEMS_BY_NICHE.get(normalized_niche)
    if (
        quotas is None
        or catalog_source_path is None
        or catalog_source_path.suffix.lower() != ".csv"
    ):
        return SelectionResult(
            scored_offers=eligible_scored_offers,
            applied_default_policy=False,
            selected_count=len(eligible_scored_offers),
            quota_count=0,
        )

    subniche_by_url = _load_first_subniche_by_url(catalog_source_path)
    selected: list[ScoredOffer] = []
    zero_sales_selected = 0
    for subniche, quota in quotas.items():
        candidates = [
            item
            for item in eligible_scored_offers
            if subniche_by_url.get(item.offer.url) == subniche
        ]
        selected_in_subniche = 0
        for candidate in candidates:
            if selected_in_subniche >= quota:
                break
            if (
                max_zero_sales_items is not None
                and candidate.offer.sales_count <= 0
                and zero_sales_selected >= max_zero_sales_items
            ):
                continue
            selected.append(candidate)
            selected_in_subniche += 1
            if candidate.offer.sales_count <= 0:
                zero_sales_selected += 1

    return SelectionResult(
        scored_offers=selected,
        applied_default_policy=True,
        selected_count=len(selected),
        quota_count=sum(quotas.values()),
    )


def resolve_selection_policy(niche: str) -> SelectionPolicy | None:
    return DEFAULT_SELECTION_POLICIES_BY_NICHE.get(niche.strip().lower())


def _filter_eligible_scored_offers(scored_offers: list[ScoredOffer]) -> list[ScoredOffer]:
    now = datetime.now(UTC)
    return [
        item
        for item in scored_offers
        if _is_offer_eligible(
            cooldown_until=item.offer.cooldown_until,
            now=now,
        )
    ]


def _is_offer_eligible(*, cooldown_until: str | None, now: datetime) -> bool:
    if not cooldown_until:
        return True
    try:
        parsed = datetime.fromisoformat(cooldown_until)
    except ValueError:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed <= now


def _load_first_subniche_by_url(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    subniche_by_url: dict[str, str] = {}
    for row in rows:
        url = (row.get("offerLink") or row.get("productLink") or "").strip()
        if not url:
            continue
        subniche_by_url[url] = _parse_first_subniche(row.get("subniches", ""))
    return subniche_by_url


def _parse_first_subniche(raw_value: str) -> str:
    if not raw_value or raw_value == "[]":
        return "sem-subnicho"
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return "sem-subnicho"
    if not isinstance(parsed, list) or not parsed:
        return "sem-subnicho"
    return str(parsed[0]).strip() or "sem-subnicho"
