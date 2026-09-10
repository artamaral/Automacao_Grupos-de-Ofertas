from __future__ import annotations

import argparse
import csv
import sys
import zipfile
from collections.abc import Iterable, Sequence
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

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
DEFAULT_ITEM_OUTPUT_PATH = Path("product_offer_v2_items.csv")
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
ITEM_BATCH_FIELDNAMES = [
    "itemIdRequested",
    "requestPage",
    "responsePage",
    "responseLimit",
    "hasNextPage",
    "scrollId",
    *CSV_FIELDNAMES,
]


class DiscoveryMode(StrEnum):
    PRODUCT_CAT_ID = "productCatId"
    ITEM_ID = "itemId"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa productOfferV2 para descoberta por productCatId ou itemId"
    )
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in DiscoveryMode],
        default=DiscoveryMode.PRODUCT_CAT_ID.value,
        help="Tipo de entrada da descoberta",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
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
    parser.add_argument(
        "--itemIds",
        default=None,
        help="Lista opcional de itemId separada por virgula; usada com --mode itemId",
    )
    parser.add_argument(
        "--inputExcel",
        type=Path,
        default=None,
        help="Arquivo .xlsx de entrada com uma coluna de ids",
    )
    parser.add_argument(
        "--inputColumn",
        default=None,
        help="Nome da coluna no Excel. Padrao: productCatId ou itemId conforme --mode",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    mode = DiscoveryMode(args.mode)
    output_path = args.output or _default_output_path(mode)

    try:
        _validate_positive("startPage", args.startPage)
        _validate_positive("maxPages", args.maxPages)
        _validate_positive("limit", args.limit)
        provider = ShopeeProvider(settings=_get_repo_settings())
        if mode is DiscoveryMode.PRODUCT_CAT_ID:
            product_cat_ids = _resolve_product_cat_ids(args)
            summary = _write_product_category_pages(
                provider=provider,
                output_path=output_path,
                product_cat_ids=product_cat_ids,
                start_page=args.startPage,
                max_pages=args.maxPages,
                limit=args.limit,
                sort_type=args.sortType,
                is_ams_offer=args.isAMSOffer,
                is_key_seller=args.isKeySeller,
            )
        else:
            item_ids = _resolve_item_ids(args)
            summary = _write_item_pages(
                provider=provider,
                output_path=output_path,
                item_ids=item_ids,
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
    print(f"CSV: {output_path}")
    print("INFO | Nenhum header, Authorization ou secret foi impresso.")
    return 0


def _default_output_path(mode: DiscoveryMode) -> Path:
    if mode is DiscoveryMode.ITEM_ID:
        return DEFAULT_ITEM_OUTPUT_PATH
    return DEFAULT_OUTPUT_PATH


def _resolve_product_cat_ids(args: argparse.Namespace) -> list[int]:
    if args.itemIds:
        raise ValueError("--itemIds deve ser usado somente com --mode itemId")
    column = args.inputColumn or "productCatId"
    ids = _parse_id_list(args.productCatIds)
    if args.inputExcel is not None:
        ids.extend(_read_ids_from_xlsx(args.inputExcel, column=column))
    return ids or DEFAULT_PRODUCT_CAT_IDS


def _resolve_item_ids(args: argparse.Namespace) -> list[int]:
    if args.productCatIds:
        raise ValueError("--productCatIds deve ser usado somente com --mode productCatId")
    column = args.inputColumn or "itemId"
    ids = _parse_id_list(args.itemIds)
    if args.inputExcel is not None:
        ids.extend(_read_ids_from_xlsx(args.inputExcel, column=column))
    if not ids:
        raise ValueError("--mode itemId exige --itemIds ou --inputExcel")
    return _deduplicate_ids(ids)


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


def _write_item_pages(
    *,
    provider: ShopeeProvider,
    output_path: Path,
    item_ids: Sequence[int],
    limit: int,
    sort_type: int,
    is_ams_offer: bool,
    is_key_seller: bool,
) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total_nodes = 0
    item_summaries: list[dict[str, Any]] = []

    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=ITEM_BATCH_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()

        for item_id in item_ids:
            params = {
                "itemId": item_id,
                "page": 1,
                "limit": limit,
                "sortType": sort_type,
                "isAMSOffer": is_ams_offer,
                "isKeySeller": is_key_seller,
            }
            response_data = _fetch_product_offer_page(provider=provider, params=params)
            connection = response_data["data"][PRODUCT_OFFER_ROOT_FIELD]
            page_info = connection.get("pageInfo", {})
            nodes = _extract_product_offer_nodes(response_data)
            total_nodes += len(nodes)
            _write_item_nodes(
                writer=writer,
                nodes=nodes,
                requested_item_id=item_id,
                page_info=page_info if isinstance(page_info, dict) else {},
            )
            print(
                "INFO | "
                f"itemId={item_id} page=1 "
                f"nodes={len(nodes)} hasNextPage={page_info.get('hasNextPage')}"
            )
            item_summaries.append(
                {
                    "itemId": item_id,
                    "nodes": len(nodes),
                    "stopReason": "ok" if nodes else "empty_page",
                }
            )

    return {
        "mode": DiscoveryMode.ITEM_ID.value,
        "itemIds": len(item_ids),
        "pages": len(item_ids),
        "nodes": total_nodes,
        "output": str(output_path),
        "items": item_summaries,
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


def _write_item_nodes(
    *,
    writer: csv.DictWriter,
    nodes: Iterable[dict[str, Any]],
    requested_item_id: int,
    page_info: dict[str, Any],
) -> None:
    for node in nodes:
        writer.writerow(
            {
                "itemIdRequested": requested_item_id,
                "requestPage": 1,
                "responsePage": page_info.get("page"),
                "responseLimit": page_info.get("limit"),
                "hasNextPage": page_info.get("hasNextPage"),
                "scrollId": page_info.get("scrollId"),
                **{field: _serialize_csv_value(node.get(field)) for field in CSV_FIELDNAMES},
            }
        )


def _parse_product_cat_ids(value: str | None) -> list[int]:
    return _parse_id_list(value)


def _parse_item_ids(value: str | None) -> list[int]:
    return _parse_id_list(value)


def _parse_id_list(value: str | None) -> list[int]:
    if value is None:
        return []
    parts = [part.strip() for part in value.split(",")]
    return _deduplicate_ids(_parse_positive_id(part, context="id") for part in parts if part)


def _deduplicate_ids(values: Iterable[int]) -> list[int]:
    ids = []
    seen = set()
    for value in values:
        _validate_positive("id", value)
        if value in seen:
            continue
        seen.add(value)
        ids.append(value)
    return ids


def _read_ids_from_xlsx(path: Path, *, column: str) -> list[int]:
    if path.suffix.lower() != ".xlsx":
        raise ValueError("--inputExcel aceita apenas arquivos .xlsx")
    if not path.exists():
        raise ValueError(f"arquivo nao encontrado: {path}")

    rows = _read_first_sheet_rows(path)
    if not rows:
        raise ValueError(f"arquivo sem linhas: {path}")

    headers = [_normalize_column_name(str(value or "")) for value in rows[0]]
    normalized_column = _normalize_column_name(column)
    try:
        column_index = headers.index(normalized_column)
    except ValueError as error:
        raise ValueError(f"coluna '{column}' nao encontrada em {path}") from error

    ids = []
    for row_number, row in enumerate(rows[1:], start=2):
        value = row[column_index] if column_index < len(row) else ""
        if value in {"", None}:
            continue
        ids.append(
            _parse_positive_id(
                value,
                context=f"valor invalido na coluna '{column}' linha {row_number}",
            )
        )
    return _deduplicate_ids(ids)


def _read_first_sheet_rows(path: Path) -> list[list[str]]:
    namespaces = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    with zipfile.ZipFile(path) as archive:
        shared_strings = _read_shared_strings(archive, namespaces)
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        first_sheet = workbook.find("main:sheets/main:sheet", namespaces)
        if first_sheet is None:
            return []
        relationship_id = first_sheet.attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ]
        rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = None
        for rel in rels.findall("pkgrel:Relationship", namespaces):
            if rel.attrib.get("Id") == relationship_id:
                target = rel.attrib["Target"]
                break
        if target is None:
            return []
        target_path = target.lstrip("/")
        sheet_path = target_path if target_path.startswith("xl/") else f"xl/{target_path}"
        sheet = ElementTree.fromstring(archive.read(sheet_path))

    rows: list[list[str]] = []
    for row in sheet.findall(".//main:sheetData/main:row", namespaces):
        values: list[str] = []
        for cell in row.findall("main:c", namespaces):
            column_index = _excel_column_index(cell.attrib.get("r", "A1"))
            while len(values) < column_index:
                values.append("")
            values.append(_read_cell_value(cell, shared_strings, namespaces))
        rows.append(values)
    return rows


def _read_shared_strings(
    archive: zipfile.ZipFile,
    namespaces: dict[str, str],
) -> list[str]:
    try:
        payload = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ElementTree.fromstring(payload)
    values = []
    for item in root.findall("main:si", namespaces):
        values.append("".join(text.text or "" for text in item.findall(".//main:t", namespaces)))
    return values


def _read_cell_value(
    cell: ElementTree.Element,
    shared_strings: Sequence[str],
    namespaces: dict[str, str],
) -> str:
    if cell.attrib.get("t") == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//main:t", namespaces))
    value = cell.find("main:v", namespaces)
    if value is None or value.text is None:
        return ""
    if cell.attrib.get("t") == "s":
        return shared_strings[int(value.text)]
    return value.text


def _excel_column_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + ord(char.upper()) - ord("A") + 1
    return index


def _normalize_column_name(value: str) -> str:
    return value.strip().lower()


def _parse_positive_id(value: Any, *, context: str) -> int:
    text = str(value).strip()
    try:
        number = Decimal(text)
    except InvalidOperation as error:
        raise ValueError(f"{context}: {value}") from error
    if number != number.to_integral_value():
        raise ValueError(f"{context}: {value}")
    parsed = int(number)
    _validate_positive("id", parsed)
    return parsed


def _validate_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} deve ser maior que zero")


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
