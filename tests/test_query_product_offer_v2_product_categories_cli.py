from __future__ import annotations

import csv
import importlib.util
import zipfile
from pathlib import Path


def load_batch_cli_module():
    script_dir = Path(__file__).resolve().parents[1] / "scripts/shopee"
    script_path = script_dir / "query_product_offer_v2_product_categories.py"
    spec = importlib.util.spec_from_file_location(
        "query_product_offer_v2_product_categories",
        script_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load query_product_offer_v2_product_categories.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_product_cat_ids_accepts_comma_list() -> None:
    module = load_batch_cli_module()

    assert module._parse_product_cat_ids("100350, 100351,100594") == [
        100350,
        100351,
        100594,
    ]


def test_parse_item_ids_accepts_comma_list() -> None:
    module = load_batch_cli_module()

    assert module._parse_item_ids("22098662014, 52857301055,22098662014") == [
        22098662014,
        52857301055,
    ]


def test_read_ids_from_xlsx_uses_named_column(tmp_path) -> None:
    module = load_batch_cli_module()
    workbook_path = tmp_path / "items.xlsx"
    _write_minimal_xlsx(
        workbook_path,
        rows=[
            ["name", "itemid"],
            ["Produto A", "22098662014.0"],
            ["Produto B", "52857301055"],
        ],
    )

    assert module._read_ids_from_xlsx(workbook_path, column="itemId") == [
        22098662014,
        52857301055,
    ]


def test_read_ids_from_xlsx_accepts_column_letter_without_header(tmp_path) -> None:
    module = load_batch_cli_module()
    workbook_path = tmp_path / "items_without_header.xlsx"
    _write_minimal_xlsx(
        workbook_path,
        rows=[
            ["", "22098662014"],
            ["", "52857301055"],
        ],
    )

    assert module._read_ids_from_xlsx(workbook_path, column="B") == [
        22098662014,
        52857301055,
    ]


def test_product_category_loop_writes_pages_until_empty(tmp_path, monkeypatch) -> None:
    module = load_batch_cli_module()
    calls = []

    def fake_fetch_product_offer_page(*, provider, params):
        calls.append(dict(params))
        if params["page"] == 1:
            return {
                "data": {
                    "productOfferV2": {
                        "nodes": [
                            {
                                "itemId": params["productCatId"] * 10,
                                "shopId": 123,
                                "productName": f"Produto {params['productCatId']}",
                                "productCatIds": [params["productCatId"]],
                                "shopType": [1],
                            }
                        ],
                        "pageInfo": {
                            "page": params["page"],
                            "limit": params["limit"],
                            "hasNextPage": True,
                            "scrollId": "scroll-1",
                        },
                    }
                }
            }
        return {
            "data": {
                "productOfferV2": {
                    "nodes": [],
                    "pageInfo": {
                        "page": params["page"],
                        "limit": params["limit"],
                        "hasNextPage": False,
                    },
                }
            }
        }

    monkeypatch.setattr(module, "_fetch_product_offer_page", fake_fetch_product_offer_page)
    output_path = tmp_path / "out.csv"

    summary = module._write_product_category_pages(
        provider=object(),
        output_path=output_path,
        product_cat_ids=[100350, 100351],
        start_page=1,
        max_pages=3,
        limit=50,
        sort_type=5,
        is_ams_offer=True,
        is_key_seller=True,
    )

    rows = list(csv.DictReader(output_path.open(encoding="utf-8-sig")))
    assert len(calls) == 4
    assert summary["productCatIds"] == 2
    assert summary["pages"] == 4
    assert summary["nodes"] == 2
    assert rows[0]["productCatId"] == "100350"
    assert rows[0]["requestPage"] == "1"
    assert rows[0]["productCatIds"] == "[100350]"
    assert rows[1]["productCatId"] == "100351"


def test_item_id_loop_writes_one_page_per_item(tmp_path, monkeypatch) -> None:
    module = load_batch_cli_module()
    calls = []

    def fake_fetch_product_offer_page(*, provider, params):
        calls.append(dict(params))
        return {
            "data": {
                "productOfferV2": {
                    "nodes": [
                        {
                            "itemId": params["itemId"],
                            "shopId": 123,
                            "productName": f"Produto {params['itemId']}",
                            "productCatIds": [100378],
                            "shopType": [1],
                        }
                    ],
                    "pageInfo": {
                        "page": params["page"],
                        "limit": params["limit"],
                        "hasNextPage": False,
                        "scrollId": "scroll-1",
                    },
                }
            }
        }

    monkeypatch.setattr(module, "_fetch_product_offer_page", fake_fetch_product_offer_page)
    output_path = tmp_path / "items.csv"

    summary = module._write_item_pages(
        provider=object(),
        output_path=output_path,
        item_ids=[22098662014, 52857301055],
        limit=1,
        sort_type=5,
        is_ams_offer=True,
        is_key_seller=True,
    )

    rows = list(csv.DictReader(output_path.open(encoding="utf-8-sig")))
    assert len(calls) == 2
    assert calls[0]["itemId"] == 22098662014
    assert calls[0]["page"] == 1
    assert summary["mode"] == "itemId"
    assert summary["itemIds"] == 2
    assert summary["pages"] == 2
    assert summary["nodes"] == 2
    assert rows[0]["itemIdRequested"] == "22098662014"
    assert rows[0]["itemId"] == "22098662014"
    assert rows[0]["productCatIds"] == "[100378]"


def _write_minimal_xlsx(path: Path, *, rows: list[list[str]]) -> None:
    rel_content_type = "application/vnd.openxmlformats-package.relationships+xml"
    workbook_content_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
    )
    worksheet_content_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
    )
    shared_strings_content_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"
    )
    office_document_type = (
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
        "officeDocument"
    )
    worksheet_type = (
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
        "worksheet"
    )
    shared_strings: list[str] = []
    shared_indexes: dict[str, int] = {}

    def shared_index(value: str) -> int:
        if value not in shared_indexes:
            shared_indexes[value] = len(shared_strings)
            shared_strings.append(value)
        return shared_indexes[value]

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{_excel_column_name(column_index)}{row_index}"
            cells.append(f'<c r="{cell_ref}" t="s"><v>{shared_index(value)}</v></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    shared_payload = "".join(
        f"<si><t>{value}</t></si>" for value in shared_strings
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            f"""
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="{rel_content_type}"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="{workbook_content_type}"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="{worksheet_content_type}"/>
  <Override PartName="/xl/sharedStrings.xml" ContentType="{shared_strings_content_type}"/>
</Types>
""".strip(),
        )
        archive.writestr(
            "_rels/.rels",
            f"""
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="{office_document_type}" Target="xl/workbook.xml"/>
</Relationships>
""".strip(),
        )
        archive.writestr(
            "xl/workbook.xml",
            """
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
</workbook>
""".strip(),
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            f"""
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="{worksheet_type}" Target="worksheets/sheet1.xml"/>
</Relationships>
""".strip(),
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f"""
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{"".join(sheet_rows)}</sheetData>
</worksheet>
""".strip(),
        )
        archive.writestr(
            "xl/sharedStrings.xml",
            f"""
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
  count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">
  {shared_payload}
</sst>
""".strip(),
        )


def _excel_column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name
