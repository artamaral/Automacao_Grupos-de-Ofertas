from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parents[1]
SRC_DIR = ROOT_DIR / "src"
for path in (SCRIPT_DIR, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from query_product_offer_v2 import (  # noqa: E402
    CSV_FIELDNAMES,
    DEFAULT_IS_AMS_OFFER,
    DEFAULT_IS_KEY_SELLER,
    DEFAULT_LIMIT,
    DEFAULT_SORT_TYPE,
    PRODUCT_OFFER_ROOT_FIELD,
    _build_query,
    _execute_real_product_offer_query,
    _extract_product_offer_nodes,
    _get_repo_settings,
    _parse_bool,
    _print_error,
    _print_json,
    _serialize_csv_value,
)

from ofertas_bot.providers.real_http_guard import RealHttpValidationError  # noqa: E402
from ofertas_bot.providers.shopee import ShopeeConfigurationError, ShopeeProvider  # noqa: E402
from ofertas_bot.providers.shopee_graphql import (  # noqa: E402
    ShopeeGraphqlPayloadError,
    raise_if_graphql_errors,
)
from ofertas_bot.providers.transport import HttpTransportError  # noqa: E402

DEFAULT_MAX_PAGES = 50
DEFAULT_OUTPUT_PATH = Path("product_offer_v2_product_categories.csv")
DEFAULT_PRODUCT_CAT_IDS = [
    100350,
    100351,
    100352,
    100353,
    100354,
    100355,
    100357,
    100358,
    100360,
    100361,
    100102,
    100103,
    100104,
    100363,
    100364,
    100365,
    100380,
    100381,
    100382,
    100387,
    100389,
    100390,
    100391,
    100400,
    100401,
    100402,
    101615,
    102029,
    102030,
    102032,
    100869,
    100871,
    100872,
    100897,
    101669,
    101670,
    100901,
    100162,
    100091,
    100092,
    100093,
    100094,
    100095,
    100338,
    100586,
    100588,
    100589,
    100590,
    100591,
    100559,
    100560,
    100593,
    100594,
]
BATCH_FIELDNAMES = [
    "productCatId",
    "requestPage",
    "responsePage",
    "responseLimit",
    "hasNextPage",
    "scrollId",
    *CSV_FIELDNAMES,
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa productOfferV2 para varios productCatId ate a pagina 50"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="CSV consolidado de saida",
    )
    parser.add_argument("--maxPages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--startPage", type=int, default=1)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--sortType", type=int, default=DEFAULT_SORT_TYPE)
    parser.add_argument("--isAMSOffer", type=_parse_bool, default=DEFAULT_IS_AMS_OFFER)
    parser.add_argument("--isKeySeller", type=_parse_bool, default=DEFAULT_IS_KEY_SELLER)
    parser.add_argument(
        "--productCatIds",
        default=None,
        help="Lista opcional separada por virgula; se omitida, usa a lista fixa do script",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    product_cat_ids = _parse_product_cat_ids(args.productCatIds) or DEFAULT_PRODUCT_CAT_IDS

    try:
        _validate_positive("startPage", args.startPage)
        _validate_positive("maxPages", args.maxPages)
        _validate_positive("limit", args.limit)
        provider = ShopeeProvider(settings=_get_repo_settings())
        summary = _write_product_category_pages(
            provider=provider,
            output_path=args.output,
            product_cat_ids=product_cat_ids,
            start_page=args.startPage,
            max_pages=args.maxPages,
            limit=args.limit,
            sort_type=args.sortType,
            is_ams_offer=args.isAMSOffer,
            is_key_seller=args.isKeySeller,
        )
    except ValueError as error:
        _print_error("Parametros invalidos", error)
        return 3
    except ShopeeConfigurationError as error:
        _print_error("Configuracao Shopee ausente ou invalida", error)
        return 3
    except RealHttpValidationError as error:
        _print_error("HTTP real da Shopee bloqueado pela configuracao atual", error)
        return 3
    except HttpTransportError as error:
        _print_error("Falha de transporte HTTP na chamada Shopee", error)
        return 2
    except ShopeeGraphqlPayloadError as error:
        _print_error("Erro GraphQL retornado pela Shopee", error)
        return 2

    print("Summary:")
    _print_json(summary)
    print(f"CSV: {args.output}")
    print("INFO | Nenhum header, Authorization ou secret foi impresso.")
    return 0


def _write_product_category_pages(
    *,
    provider: ShopeeProvider,
    output_path: Path,
    product_cat_ids: Sequence[int],
    start_page: int,
    max_pages: int,
    limit: int,
    sort_type: int,
    is_ams_offer: bool,
    is_key_seller: bool,
) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total_nodes = 0
    total_pages = 0
    category_summaries: list[dict[str, Any]] = []

    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=BATCH_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()

        for product_cat_id in product_cat_ids:
            category_nodes = 0
            category_pages = 0
            stop_reason = "max_pages_reached"
            last_page = start_page - 1

            for page in range(start_page, max_pages + 1):
                params = {
                    "productCatId": product_cat_id,
                    "page": page,
                    "limit": limit,
                    "sortType": sort_type,
                    "isAMSOffer": is_ams_offer,
                    "isKeySeller": is_key_seller,
                }
                response_data = _fetch_product_offer_page(provider=provider, params=params)
                connection = response_data["data"][PRODUCT_OFFER_ROOT_FIELD]
                page_info = connection.get("pageInfo", {})
                nodes = _extract_product_offer_nodes(response_data)

                category_pages += 1
                total_pages += 1
                last_page = page
                category_nodes += len(nodes)
                total_nodes += len(nodes)
                _write_nodes(
                    writer=writer,
                    nodes=nodes,
                    product_cat_id=product_cat_id,
                    request_page=page,
                    page_info=page_info if isinstance(page_info, dict) else {},
                )
                print(
                    "INFO | "
                    f"productCatId={product_cat_id} page={page} "
                    f"nodes={len(nodes)} hasNextPage={page_info.get('hasNextPage')}"
                )

                if not nodes:
                    stop_reason = "empty_page"
                    break
                if page_info.get("hasNextPage") is not True:
                    stop_reason = "has_next_page_false"
                    break

            category_summaries.append(
                {
                    "productCatId": product_cat_id,
                    "pages": category_pages,
                    "nodes": category_nodes,
                    "lastPage": last_page,
                    "stopReason": stop_reason,
                }
            )

    return {
        "productCatIds": len(product_cat_ids),
        "pages": total_pages,
        "nodes": total_nodes,
        "output": str(output_path),
        "categories": category_summaries,
    }


def _fetch_product_offer_page(
    *,
    provider: ShopeeProvider,
    params: dict[str, Any],
) -> dict[str, Any]:
    query = _build_query(params)
    response = _execute_real_product_offer_query(provider=provider, query=query)
    if not response.ok:
        print(f"ERRO | Shopee request failed with status={response.status_code}", file=sys.stderr)
        print("Parameters:", file=sys.stderr)
        _print_json(params, stream=sys.stderr)
        print("Payload:", file=sys.stderr)
        _print_json(response.data, stream=sys.stderr)
        raise ShopeeGraphqlPayloadError("Shopee HTTP response failed")

    try:
        raise_if_graphql_errors(response.data)
    except ShopeeGraphqlPayloadError as error:
        print("Parameters:", file=sys.stderr)
        _print_json(params, stream=sys.stderr)
        print("Payload:", file=sys.stderr)
        _print_json(response.data, stream=sys.stderr)
        if "page not found" in str(error).lower():
            return {
                "data": {
                    PRODUCT_OFFER_ROOT_FIELD: {
                        "nodes": [],
                        "pageInfo": {
                            "page": params["page"],
                            "limit": params["limit"],
                            "hasNextPage": False,
                        },
                    }
                }
            }
        raise

    return response.data


def _write_nodes(
    *,
    writer: csv.DictWriter,
    nodes: Iterable[dict[str, Any]],
    product_cat_id: int,
    request_page: int,
    page_info: dict[str, Any],
) -> None:
    for node in nodes:
        writer.writerow(
            {
                "productCatId": product_cat_id,
                "requestPage": request_page,
                "responsePage": page_info.get("page"),
                "responseLimit": page_info.get("limit"),
                "hasNextPage": page_info.get("hasNextPage"),
                "scrollId": page_info.get("scrollId"),
                **{field: _serialize_csv_value(node.get(field)) for field in CSV_FIELDNAMES},
            }
        )


def _parse_product_cat_ids(value: str | None) -> list[int]:
    if value is None:
        return []
    parts = [part.strip() for part in value.split(",")]
    return [int(part) for part in parts if part]


def _validate_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} deve ser maior que zero")


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
