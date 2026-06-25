from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ofertas_bot.discovery_profiles import DiscoveryProfile, DiscoveryProfileError, load_discovery_profile_catalog
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.providers.shopee_graphql import ShopeeGraphqlPayloadError
from ofertas_bot.settings import get_settings


DEFAULT_OUTPUT_DIR = Path("tmp")
DEFAULT_PAGE_SIZE = 50
DEFAULT_MAX_PAGES = 50
DEFAULT_OFFER_SEARCH_LIMIT = 50


@dataclass(frozen=True)
class ScenarioSpec:
    slug: str
    description: str
    offer_keyword: str | None = None
    product_params: dict[str, Any] | None = None
    use_offer_discovery: bool = False


@dataclass(frozen=True)
class ScenarioResult:
    slug: str
    description: str
    row_count: int
    unique_item_count: int
    duplicate_item_count: int
    page_count: int
    total_nodes: int
    stop_reason: str
    stop_page: int | None
    match_ids: list[int]
    sample_titles: list[str]
    csv_path: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Roda cenarios comparativos de descoberta Shopee para um profile"
    )
    parser.add_argument("--profile", required=True, help="Slug do profile versionado")
    parser.add_argument(
        "--profiles-file",
        default="config/discovery_profiles.toml",
        help="Arquivo TOML com profiles de descoberta",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Diretorio de saida para CSVs e resumo JSON",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help="Itens por pagina para productOfferV2",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help="Numero maximo de paginas por cenario",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        profile = _load_profile(Path(args.profiles_file), args.profile)
    except DiscoveryProfileError as error:
        print(f"ERRO | {error}")
        return 3

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    provider = ShopeeProvider(settings=get_settings())
    provider.validate_real_http_ready()

    scenarios = _build_scenarios(profile)
    results: list[ScenarioResult] = []
    scenario_items: dict[str, set[str]] = {}

    for scenario in scenarios:
        result, item_keys = _execute_scenario(
            provider=provider,
            profile=profile,
            scenario=scenario,
            page_size=args.page_size,
            max_pages=args.max_pages,
            output_dir=output_dir,
        )
        results.append(result)
        scenario_items[scenario.slug] = item_keys

    overlaps = _build_overlaps(results=results, scenario_items=scenario_items)
    summary_path = output_dir / f"shopee-discovery-matrix-{profile.slug}.json"
    summary_path.write_text(
        json.dumps(
            {
                "profile": {
                    "slug": profile.slug,
                    "name": profile.name,
                    "niche": profile.niche,
                    "search_term": profile.search_term(),
                    "shopee_offer_keyword": profile.shopee_offer_keyword,
                },
                "scenarios": [asdict(result) for result in results],
                "overlaps": overlaps,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"INFO | Matriz Shopee salva em {summary_path}")
    for result in results:
        print(
            "INFO | "
            f"scenario={result.slug} rows={result.row_count} unique={result.unique_item_count} "
            f"pages={result.page_count} stop={result.stop_reason}"
        )
    return 0


def _load_profile(path: Path, slug: str) -> DiscoveryProfile:
    profile = load_discovery_profile_catalog(path).get(slug)
    if profile is None:
        raise DiscoveryProfileError(f"profile nao encontrado: {slug}")
    return profile


def _build_scenarios(profile: DiscoveryProfile) -> list[ScenarioSpec]:
    scenarios = [
        ScenarioSpec(
            slug="shopeeOfferV2_keyword__productOfferV2_listType_4_matchId_categoryId",
            description="shopeeOfferV2(keyword) seguido de productOfferV2(listType=4, matchId=categoryId)",
            offer_keyword=profile.shopee_offer_keyword,
            use_offer_discovery=True,
        ),
        ScenarioSpec(
            slug="productOfferV2_keyword_niche",
            description="productOfferV2(keyword=profile.niche)",
            product_params={"keyword": profile.niche},
        ),
        ScenarioSpec(
            slug="productOfferV2_keyword_search_term",
            description="productOfferV2(keyword=profile.search_term())",
            product_params={"keyword": profile.search_term()},
        ),
        ScenarioSpec(
            slug="productOfferV2_page_limit_only",
            description="productOfferV2(page, limit)",
            product_params={},
        ),
        ScenarioSpec(
            slug="productOfferV2_listType_1_sortType_2_isKeySeller_true",
            description="productOfferV2(listType=1, sortType=2, isKeySeller=true)",
            product_params={"list_type": 1, "sort_type": 2, "is_key_seller": True},
        ),
    ]
    deduplicated: list[ScenarioSpec] = []
    seen_signatures: set[str] = set()
    for scenario in scenarios:
        signature = json.dumps(
            {
                "offer_keyword": scenario.offer_keyword,
                "product_params": scenario.product_params,
                "use_offer_discovery": scenario.use_offer_discovery,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        deduplicated.append(scenario)
    return deduplicated


def _execute_scenario(
    *,
    provider: ShopeeProvider,
    profile: DiscoveryProfile,
    scenario: ScenarioSpec,
    page_size: int,
    max_pages: int,
    output_dir: Path,
) -> tuple[ScenarioResult, set[str]]:
    match_ids: list[int] = []
    if scenario.use_offer_discovery:
        if not scenario.offer_keyword:
            raise DiscoveryProfileError(
                f"scenario {scenario.slug} requer shopee_offer_keyword configurado"
            )
        offer_response = provider.fetch_offer_search_raw_response(
            scenario.offer_keyword,
            DEFAULT_OFFER_SEARCH_LIMIT,
        )
        match_ids = _extract_category_match_ids(offer_response)
        if not match_ids:
            stop_reason = "no_match_id"
            csv_path = output_dir / f"shopee-{profile.slug}-{scenario.slug}.csv"
            _write_scenario_csv(csv_path, [])
            return (
                ScenarioResult(
                    slug=scenario.slug,
                    description=scenario.description,
                    row_count=0,
                    unique_item_count=0,
                    duplicate_item_count=0,
                    page_count=0,
                    total_nodes=0,
                    stop_reason=stop_reason,
                    stop_page=None,
                    match_ids=[],
                    sample_titles=[],
                    csv_path=str(csv_path),
                ),
                set(),
            )
    else:
        match_ids = [None]

    rows: list[dict[str, Any]] = []
    item_keys: set[str] = set()
    total_nodes = 0
    page_count = 0
    stop_reason = "max_pages_reached"
    stop_page: int | None = None
    sample_titles: list[str] = []

    for match_id in match_ids:
        for page in range(1, max_pages + 1):
            params = dict(scenario.product_params or {})
            params.setdefault("limit", page_size)
            params.setdefault("page", page)
            if match_id is not None:
                params["match_id"] = match_id
                params.setdefault("list_type", 4)
            try:
                response = provider.fetch_product_offer_raw_response(**params)
            except ShopeeGraphqlPayloadError as error:
                if _is_page_not_found_error(error):
                    stop_reason = "page_not_found"
                    stop_page = page
                    break
                raise

            connection = response.get("data", {}).get("productOfferV2", {})
            product_nodes = connection.get("nodes", []) if isinstance(connection, dict) else []
            page_info = connection.get("pageInfo", {}) if isinstance(connection, dict) else {}
            node_count = len(product_nodes) if isinstance(product_nodes, list) else 0
            total_nodes += node_count
            page_count += 1

            for node in product_nodes:
                if not isinstance(node, dict):
                    continue
                item_key = _build_item_key(node)
                item_keys.add(item_key)
                if len(sample_titles) < 5:
                    title = str(node.get("productName", "")).strip()
                    if title:
                        sample_titles.append(title)
                rows.append(
                    {
                        "scenario": scenario.slug,
                        "profileSlug": profile.slug,
                        "niche": profile.niche,
                        "offerKeyword": scenario.offer_keyword,
                        "matchId": match_id,
                        "page": page_info.get("page"),
                        "limit": page_info.get("limit"),
                        "hasNextPage": page_info.get("hasNextPage"),
                        "scrollId": page_info.get("scrollId"),
                        "itemId": node.get("itemId"),
                        "commissionRate": node.get("commissionRate"),
                        "appExistRate": node.get("appExistRate"),
                        "appNewRate": node.get("appNewRate"),
                        "webExistRate": node.get("webExistRate"),
                        "webNewRate": node.get("webNewRate"),
                        "commission": node.get("commission"),
                        "price": node.get("price"),
                        "sales": node.get("sales"),
                        "imageUrl": node.get("imageUrl"),
                        "productName": node.get("productName"),
                        "shopName": node.get("shopName"),
                        "productLink": node.get("productLink"),
                        "offerLink": node.get("offerLink"),
                        "periodEndTime": node.get("periodEndTime"),
                        "periodStartTime": node.get("periodStartTime"),
                        "priceMin": node.get("priceMin"),
                        "priceMax": node.get("priceMax"),
                        "productCatIds": json.dumps(node.get("productCatIds"), ensure_ascii=False),
                        "ratingStar": node.get("ratingStar"),
                        "priceDiscountRate": node.get("priceDiscountRate"),
                        "shopId": node.get("shopId"),
                        "shopType": json.dumps(node.get("shopType"), ensure_ascii=False),
                        "sellerCommissionRate": node.get("sellerCommissionRate"),
                        "shopeeCommissionRate": node.get("shopeeCommissionRate"),
                    }
                )

            has_next_page = page_info.get("hasNextPage")
            if node_count == 0:
                stop_reason = "empty_page"
                stop_page = page
                break
            if has_next_page is not True:
                stop_reason = "has_next_page_false"
                stop_page = page
                break
        if stop_reason != "max_pages_reached":
            break

    csv_path = output_dir / f"shopee-{profile.slug}-{scenario.slug}.csv"
    _write_scenario_csv(csv_path, rows)
    return (
        ScenarioResult(
            slug=scenario.slug,
            description=scenario.description,
            row_count=len(rows),
            unique_item_count=len(item_keys),
            duplicate_item_count=len(rows) - len(item_keys),
            page_count=page_count,
            total_nodes=total_nodes,
            stop_reason=stop_reason,
            stop_page=stop_page,
            match_ids=[match_id for match_id in match_ids if isinstance(match_id, int)],
            sample_titles=sample_titles,
            csv_path=str(csv_path),
        ),
        item_keys,
    )


def _extract_category_match_ids(response_data: dict[str, Any]) -> list[int]:
    data = response_data.get("data")
    if not isinstance(data, dict):
        return []
    connection = data.get("shopeeOfferV2")
    if not isinstance(connection, dict):
        return []
    nodes = connection.get("nodes")
    if not isinstance(nodes, list):
        return []
    match_ids: list[int] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        category_id = node.get("categoryId")
        if isinstance(category_id, int) and category_id not in match_ids:
            match_ids.append(category_id)
    return match_ids


def _is_page_not_found_error(error: Exception) -> bool:
    return "page not found" in str(error).strip().lower()


def _build_item_key(node: dict[str, Any]) -> str:
    return f"{node.get('shopId')}:{node.get('itemId')}"


def _write_scenario_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "scenario",
        "profileSlug",
        "niche",
        "offerKeyword",
        "matchId",
        "page",
        "limit",
        "hasNextPage",
        "scrollId",
        "itemId",
        "commissionRate",
        "appExistRate",
        "appNewRate",
        "webExistRate",
        "webNewRate",
        "commission",
        "price",
        "sales",
        "imageUrl",
        "productName",
        "shopName",
        "productLink",
        "offerLink",
        "periodEndTime",
        "periodStartTime",
        "priceMin",
        "priceMax",
        "productCatIds",
        "ratingStar",
        "priceDiscountRate",
        "shopId",
        "shopType",
        "sellerCommissionRate",
        "shopeeCommissionRate",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_overlaps(
    *,
    results: list[ScenarioResult],
    scenario_items: dict[str, set[str]],
) -> list[dict[str, Any]]:
    overlaps: list[dict[str, Any]] = []
    for index, left in enumerate(results):
        for right in results[index + 1 :]:
            left_items = scenario_items.get(left.slug, set())
            right_items = scenario_items.get(right.slug, set())
            intersection = left_items & right_items
            smaller_base = min(len(left_items), len(right_items)) or 1
            overlaps.append(
                {
                    "left": left.slug,
                    "right": right.slug,
                    "intersection_count": len(intersection),
                    "left_count": len(left_items),
                    "right_count": len(right_items),
                    "intersection_pct_of_smaller": round(len(intersection) / smaller_base, 4),
                }
            )
    return overlaps


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
