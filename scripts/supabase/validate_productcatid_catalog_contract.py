from __future__ import annotations

import argparse
from pathlib import Path

from ofertas_bot.catalog_contract import OPERATIONAL_CATALOG_FIELDNAMES
from ofertas_bot.productcatid_catalog import (
    load_product_category_quotas,
    validate_quotas_against_category_csv,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the feminino singular productCatId contract."
    )
    parser.add_argument(
        "--matrix", type=Path, default=Path("config/shopee_productcatid_quotas_feminino.csv")
    )
    parser.add_argument(
        "--categories", type=Path, default=Path("data/shopee_product_categories.csv")
    )
    args = parser.parse_args()
    quotas = load_product_category_quotas(args.matrix)
    validate_quotas_against_category_csv(quotas, args.categories)
    if "productCatId" not in OPERATIONAL_CATALOG_FIELDNAMES:
        raise SystemExit("productCatId missing from operational catalog contract")
    if "productCatIds" in OPERATIONAL_CATALOG_FIELDNAMES:
        raise SystemExit("response productCatIds must not be operational")
    daily_total = sum(item.daily_quantity for item in quotas)
    print(f"PRODUCTCATID_CONTRACT=OK categories={len(quotas)} daily_total={daily_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
