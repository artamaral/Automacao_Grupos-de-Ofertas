from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from time import time
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ofertas_bot.providers.http import HttpResponse  # noqa: E402
from ofertas_bot.providers.real_http_guard import RealHttpValidationError  # noqa: E402
from ofertas_bot.providers.shopee import ShopeeConfigurationError, ShopeeProvider  # noqa: E402
from ofertas_bot.providers.shopee_graphql import (  # noqa: E402
    SHOPEE_PRODUCT_OFFER_LIST_OPERATION,
    ShopeeGraphqlPayloadError,
    build_graphql_request,
    build_product_offer_query,
    raise_if_graphql_errors,
)
from ofertas_bot.providers.transport import HttpTransportError  # noqa: E402
from ofertas_bot.settings import get_settings  # noqa: E402

DEFAULT_PAGE = 1
DEFAULT_LIMIT = 50
DEFAULT_SORT_TYPE = 5
DEFAULT_IS_AMS_OFFER = True
DEFAULT_IS_KEY_SELLER = True
PRODUCT_OFFER_ROOT_FIELD = "productOfferV2"
CSV_FIELDNAMES = [
    "itemId",
    "commissionRate",
    "appExistRate",
    "appNewRate",
    "webExistRate",
    "webNewRate",
    "commission",
    "price",
    "sales",
    "shopId",
    "productName",
    "imageUrl",
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
    "shopType",
    "sellerCommissionRate",
    "shopeeCommissionRate",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa manualmente a query Shopee productOfferV2"
    )
    parser.add_argument("--listType", type=int, default=None)
    parser.add_argument("--matchId", type=int, default=None)
    parser.add_argument("--page", type=int, default=DEFAULT_PAGE)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--sortType", type=int, default=DEFAULT_SORT_TYPE)
    parser.add_argument("--itemId", type=int, default=None)
    parser.add_argument("--shopId", type=int, default=None)
    parser.add_argument("--productCatId", type=int, default=None)
    parser.add_argument("--isAMSOffer", type=_parse_bool, default=DEFAULT_IS_AMS_OFFER)
    parser.add_argument("--isKeySeller", type=_parse_bool, default=DEFAULT_IS_KEY_SELLER)
    parser.add_argument("--csv", nargs="?", const="", default=None)
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    params = _build_effective_params(args)
    query = _build_query(params)

    try:
        provider = ShopeeProvider(settings=get_settings())
        response = _execute_real_product_offer_query(provider=provider, query=query)
        raise_if_graphql_errors(response.data)
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
        _print_diagnostic_context(params=params, query=query, stream=sys.stderr)
        print("Payload:", file=sys.stderr)
        _print_json(response.data, stream=sys.stderr)
        return 2

    if not response.ok:
        print(f"ERRO | Shopee request failed with status={response.status_code}", file=sys.stderr)
        _print_diagnostic_context(params=params, query=query, stream=sys.stderr)
        print("Payload:", file=sys.stderr)
        _print_json(response.data, stream=sys.stderr)
        return 2

    if args.csv is not None:
        try:
            nodes = _extract_product_offer_nodes(response.data)
        except ShopeeGraphqlPayloadError as error:
            _print_error("Resposta Shopee invalida para exportacao CSV", error)
            _print_diagnostic_context(params=params, query=query, stream=sys.stderr)
            print("Payload:", file=sys.stderr)
            _print_json(response.data, stream=sys.stderr)
            return 2
        csv_path = _resolve_csv_path(csv_arg=args.csv, list_type=params.get("listType"))
        _write_nodes_csv(csv_path, nodes)
        print(f"INFO | nodes_recebidos={len(nodes)}")
        print(f"INFO | csv={csv_path}")
        print("INFO | Nenhum header, Authorization ou secret foi impresso.")
        return 0

    print("Parameters:")
    _print_json(params)
    print()
    print("GraphQL:")
    print(query)
    print()
    print("Response:")
    _print_json(response.data)
    return 0


def _build_effective_params(args: argparse.Namespace) -> dict[str, Any]:
    params = {
        "listType": args.listType,
        "matchId": args.matchId,
        "page": args.page,
        "limit": args.limit,
        "keyword": args.keyword,
        "sortType": args.sortType,
        "itemId": args.itemId,
        "shopId": args.shopId,
        "productCatId": args.productCatId,
        "isAMSOffer": args.isAMSOffer,
        "isKeySeller": args.isKeySeller,
    }
    return {key: value for key, value in params.items() if value is not None}


def _build_query(params: dict[str, Any]) -> str:
    return build_product_offer_query(
        list_type=params.get("listType"),
        match_id=params.get("matchId"),
        page=params["page"],
        limit=params["limit"],
        keyword=params.get("keyword"),
        sort_type=params.get("sortType"),
        item_id=params.get("itemId"),
        shop_id=params.get("shopId"),
        product_cat_id=params.get("productCatId"),
        is_ams_offer=params.get("isAMSOffer"),
        is_key_seller=params.get("isKeySeller"),
    )


def _execute_real_product_offer_query(
    *,
    provider: ShopeeProvider,
    query: str,
) -> HttpResponse:
    provider._validate_configuration()
    provider.validate_real_http_ready()
    gateway = provider._get_graphql_gateway()
    if gateway.transport is None:
        msg = "Shopee GraphQL transport is not configured"
        raise RealHttpValidationError(msg)

    request = build_graphql_request(
        graphql_url=gateway.offer_list_builder.graphql_url,
        signer=gateway.offer_list_builder.signer,
        timestamp=int(time()),
        query=query,
        operation_name=SHOPEE_PRODUCT_OFFER_LIST_OPERATION,
        variables={},
    )
    return gateway.transport.send(request)


def _extract_product_offer_nodes(response_data: dict[str, Any]) -> list[dict[str, Any]]:
    data = response_data.get("data")
    if not isinstance(data, dict):
        msg = "Shopee GraphQL response field 'data' must be an object"
        raise ShopeeGraphqlPayloadError(msg)

    connection = data.get(PRODUCT_OFFER_ROOT_FIELD)
    if not isinstance(connection, dict):
        msg = "Shopee GraphQL response field 'data.productOfferV2' must be an object"
        raise ShopeeGraphqlPayloadError(msg)

    nodes = connection.get("nodes")
    if not isinstance(nodes, list):
        msg = "Shopee GraphQL response field 'data.productOfferV2.nodes' must be a list"
        raise ShopeeGraphqlPayloadError(msg)

    invalid_items = [index for index, node in enumerate(nodes) if not isinstance(node, dict)]
    if invalid_items:
        msg = "Shopee GraphQL response field 'data.productOfferV2.nodes' must contain objects"
        raise ShopeeGraphqlPayloadError(msg)
    return nodes


def _resolve_csv_path(*, csv_arg: str, list_type: Any) -> Path:
    if csv_arg:
        return Path(csv_arg)
    if list_type is not None:
        return Path(f"product_offer_v2_{list_type}.csv")
    return Path("product_offer_v2.csv")


def _write_nodes_csv(path: Path, nodes: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for node in nodes:
            writer.writerow(
                {
                    field: _serialize_csv_value(node.get(field))
                    for field in CSV_FIELDNAMES
                }
            )


def _serialize_csv_value(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise argparse.ArgumentTypeError("booleano deve ser true, false, 1 ou 0")


def _print_error(summary: str, error: Exception) -> None:
    print(f"ERRO | {summary}", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)


def _print_diagnostic_context(
    *,
    params: dict[str, Any],
    query: str,
    stream: Any,
) -> None:
    print("Parameters:", file=stream)
    _print_json(params, stream=stream)
    print("GraphQL:", file=stream)
    print(query, file=stream)


def _print_json(payload: Any, *, stream: Any = sys.stdout) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2), file=stream)


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
