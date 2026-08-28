from __future__ import annotations

import argparse
import csv
import re
import sys
from collections.abc import Sequence
from pathlib import Path

URL = "https://seller.shopee.ph/edu/category-guide/"
DEFAULT_OUTPUT = Path("data/shopee_product_categories.csv")
FIELDNAMES = [
    "category",
    "sub_category",
    "level_3",
    "level_4",
    "level_5",
    "category_id",
]
ROW_SELECTOR = "tr.shopee-table__row"
MAX_PAGES = 1000


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extrai a tabela oficial Shopee Product Category Guide."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES)
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "ERRO | Playwright nao esta instalado. Rode: "
            ".\\.venv\\Scripts\\python.exe -m pip install playwright",
            file=sys.stderr,
        )
        return 2

    rows_by_id: dict[str, dict[str, str]] = {}
    pages_processed = 0
    warnings: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        page = browser.new_page()

        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
            _wait_for_table(page)

            while True:
                if pages_processed >= args.max_pages:
                    raise RuntimeError(f"max_pages excedido: {args.max_pages}")

                page_rows, page_warnings = _extract_rows(page)
                warnings.extend(page_warnings)
                added = 0
                for row in page_rows:
                    category_id = row["category_id"]
                    if category_id not in rows_by_id:
                        rows_by_id[category_id] = row
                        added += 1

                pages_processed += 1
                print(
                    f"Page {pages_processed}: {len(page_rows)} rows extracted "
                    f"({added} new)"
                )

                before_signature = _current_category_id_signature(page)
                next_button = _find_next_button(page)
                if next_button is None:
                    break

                next_button.click()
                try:
                    page.wait_for_function(
                        """previous => {
                            const ids = Array.from(
                                document.querySelectorAll('tr.shopee-table__row')
                            ).map(row => {
                                const cells = row.querySelectorAll('td');
                                return cells.length >= 6
                                    ? cells[5].innerText.trim()
                                    : '';
                            }).filter(Boolean).join('|');
                            return ids && ids !== previous;
                        }""",
                        arg=before_signature,
                        timeout=15_000,
                    )
                except PlaywrightTimeoutError as error:
                    raise RuntimeError(
                        "a tabela nao mudou apos clicar em next; "
                        "interrompendo para evitar loop infinito"
                    ) from error
                _wait_for_table(page)
        finally:
            browser.close()

    _write_csv(args.output, list(rows_by_id.values()))
    _validate_csv(args.output)

    for warning in warnings:
        print(f"WARNING | {warning}", file=sys.stderr)
    print(f"Pages processed: {pages_processed}")
    print(f"Rows extracted: {len(rows_by_id)}")
    print(f"Unique category IDs: {len(rows_by_id)}")
    print(f"CSV: {args.output}")
    return 0


def _wait_for_table(page) -> None:
    page.wait_for_selector(ROW_SELECTOR, timeout=30_000)
    page.wait_for_function(
        """() => Array.from(document.querySelectorAll('tr.shopee-table__row')).some(row => {
                const cells = row.querySelectorAll('td');
                return cells.length >= 6 && /^\\d+$/.test(cells[5].innerText.trim());
            })""",
        timeout=30_000,
    )


def _extract_rows(page) -> tuple[list[dict[str, str]], list[str]]:
    extracted: list[dict[str, str]] = []
    warnings: list[str] = []
    rows = page.locator(ROW_SELECTOR)

    for row_index in range(rows.count()):
        cells = rows.nth(row_index).locator("td")
        cell_count = cells.count()
        if cell_count < 6:
            warnings.append(f"linha {row_index + 1} ignorada: {cell_count} td")
            continue

        values = [_normalize(cells.nth(index).inner_text()) for index in range(6)]
        category_id = values[5]
        if not category_id.isdigit():
            warnings.append(
                f"linha {row_index + 1} ignorada: category_id invalido={category_id!r}"
            )
            continue

        extracted.append(dict(zip(FIELDNAMES, values, strict=True)))

    return extracted, warnings


def _find_next_button(page):
    selectors = [
        "button.shopee-pager__button-next",
        ".shopee-pager__button-next",
        "button.shopee-pagination-next",
        ".shopee-pagination-next",
        "button[aria-label*='next' i]",
        "button[title*='next' i]",
        "li[aria-label*='next' i] button",
    ]
    for selector in selectors:
        locator = page.locator(selector)
        for index in range(locator.count()):
            candidate = locator.nth(index)
            if candidate.is_visible() and not _is_disabled(candidate):
                return candidate

    buttons = page.locator("button")
    for index in range(buttons.count()):
        candidate = buttons.nth(index)
        if not candidate.is_visible() or _is_disabled(candidate):
            continue
        marker = candidate.evaluate(
            """el => [
                el.innerText,
                el.getAttribute('aria-label'),
                el.getAttribute('title'),
                el.className,
                el.parentElement ? el.parentElement.className : ''
            ].filter(Boolean).join(' ').toLowerCase()"""
        )
        if "next" in marker or "right" in marker:
            return candidate

    return None


def _is_disabled(locator) -> bool:
    return bool(
        locator.evaluate(
            """el => {
                const classText = [
                    el.className,
                    el.parentElement ? el.parentElement.className : ''
                ].filter(Boolean).join(' ').toLowerCase();
                return el.disabled
                    || el.getAttribute('aria-disabled') === 'true'
                    || classText.includes('disabled');
            }"""
        )
    )


def _current_category_id_signature(page) -> str:
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('tr.shopee-table__row'))
            .map(row => {
                const cells = row.querySelectorAll('td');
                return cells.length >= 6 ? cells[5].innerText.trim() : '';
            })
            .filter(Boolean)
            .join('|')"""
    )


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _validate_csv(path: Path) -> None:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        if header != FIELDNAMES:
            raise RuntimeError(f"cabecalho invalido: {header!r}")

        seen: set[str] = set()
        for line_number, row in enumerate(reader, start=2):
            if len(row) != len(FIELDNAMES):
                raise RuntimeError(f"linha {line_number} tem {len(row)} campos")
            category_id = row[5]
            if not category_id.isdigit():
                raise RuntimeError(f"linha {line_number} category_id invalido")
            if category_id in seen:
                raise RuntimeError(f"category_id duplicado: {category_id}")
            seen.add(category_id)


if __name__ == "__main__":
    raise SystemExit(run())
