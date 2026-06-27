from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from ofertas_bot.models import ScoredOffer

DEFAULT_SUBNICHE_QUOTAS_BY_NICHE: dict[str, dict[str, int]] = {
    "mae e bebe": {
        "amamentacao-extracao-leite": 2,
        "roupas-body": 2,
        "quarto-monitoramento": 2,
        "higiene-saude-unhas": 2,
        "higiene-saude-aspiradores-nasais": 1,
        "passeio-canguru-ergonomico": 1,
        "roupas-geral": 1,
        "enxoval-kits": 1,
        "alimentacao-mamadeiras": 1,
        "oral-mordedores-chupetas": 1,
        "alimentacao-copos-treinamento": 1,
        "maternidade-bolsas-mochilas": 1,
        "troca-trocadores-portateis": 1,
        "brinquedos-montessori": 1,
        "passeio-carrinhos": 1,
        "banho-banheiras": 1,
    }
}
DEFAULT_MAX_ZERO_SALES_ITEMS_BY_NICHE: dict[str, int] = {
    "mae e bebe": 4,
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
    quotas = DEFAULT_SUBNICHE_QUOTAS_BY_NICHE.get(normalized_niche)
    max_zero_sales_items = DEFAULT_MAX_ZERO_SALES_ITEMS_BY_NICHE.get(normalized_niche)
    if (
        quotas is None
        or catalog_source_path is None
        or catalog_source_path.suffix.lower() != ".csv"
    ):
        return SelectionResult(
            scored_offers=scored_offers,
            applied_default_policy=False,
            selected_count=len(scored_offers),
            quota_count=0,
        )

    subniche_by_url = _load_first_subniche_by_url(catalog_source_path)
    selected: list[ScoredOffer] = []
    zero_sales_selected = 0
    for subniche, quota in quotas.items():
        candidates = [
            item
            for item in scored_offers
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
